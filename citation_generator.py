import json
import re
import os
import logging
from typing import Dict, List, Optional
from Bio import Entrez
import time
from gemini_api import GeminiAPI

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CitationGenerator:
    """Generates and manages citations for thesis chapters."""
    
    def __init__(self, gemini_api: GeminiAPI, email: str):
        """Initialize the CitationGenerator.
        
        Args:
            gemini_api: Instance of GeminiAPI for citation analysis
            email: Email for PubMed API access
        """
        self.gemini_api = gemini_api
        Entrez.email = email
        
    def process_chapters(self, debug_folder: str) -> bool:
        """Process all chapter files in the debug folder and add citations.
        
        Args:
            debug_folder: Path to the debug folder containing chapter files
            
        Returns:
            bool: True if processing was successful, False otherwise
        """
        try:
            # Find all chapter markdown files
            citation_chapters = ['introduction', 'related_works', 'results']
            chapter_files = [f for f in os.listdir(debug_folder) 
                           if f.endswith('_chapter.md')]
            
            if not chapter_files:
                logger.error(f"No chapter files found in {debug_folder}")
                return False
                
            all_papers = []
            citation_data_by_chapter = {}
            
            # Process each chapter
            for chapter_file in chapter_files:
                chapter_path = os.path.join(debug_folder, chapter_file)
                chapter_name = chapter_file.replace('_chapter.md', '')
                
                # Only process citations for specific chapters
                if chapter_name in citation_chapters:
                    logger.info(f"Processing citations for {chapter_file}")
                    
                    # Analyze chapter for citations
                    citation_data = self._analyze_chapter(chapter_path)
                    if citation_data:
                        # Store citation data
                        citation_data_by_chapter[chapter_file] = citation_data
                        
                        # Generate citations
                        papers = self._generate_citations(citation_data)
                        all_papers.extend(papers)
                else:
                    # For non-citation chapters, just create the _cited version without modifications
                    base_name = os.path.splitext(os.path.basename(chapter_path))[0]
                    output_path = os.path.join(debug_folder, f"{base_name}_cited.md")
                    with open(chapter_path, "r", encoding="utf-8") as f:
                        text = f.read()
                    with open(output_path, "w", encoding="utf-8") as f:
                        f.write(text)
                    logger.info(f"Created cited version without citations for {chapter_file}")
            
            if not all_papers:
                logger.warning("No citations were generated for any chapter")
                return False
                
            # Export all citations to BibTeX
            bibtex_file = os.path.join(debug_folder, "references.bib")
            bibtex_keys = self._export_bibtex(all_papers, bibtex_file)
            
            # Update each chapter with citations
            for chapter_file, citation_data in citation_data_by_chapter.items():
                chapter_path = os.path.join(debug_folder, chapter_file)
                self._update_chapter_citations(
                    chapter_path,
                    citation_data,
                    bibtex_keys,
                    debug_folder
                )
                
            logger.info("Successfully processed all chapters for citations")
            return True
            
        except Exception as e:
            logger.error(f"Error processing chapters for citations: {e}")
            return False
            
    def _analyze_chapter(self, chapter_path: str) -> Optional[Dict]:
        """Analyze a chapter file for sentences requiring citations.
        
        Args:
            chapter_path: Path to the chapter markdown file
            
        Returns:
            Dictionary containing citation analysis or None if analysis fails
        """
        if not os.path.exists(chapter_path):
            logger.error(f"Chapter file not found: {chapter_path}")
            return None
            
        try:
            with open(chapter_path, "r", encoding="utf-8") as f:
                chapter_text = f.read()
                
            citation_data = self._analyze_citations(chapter_text)
            print(citation_data)
            logger.info(f"Analyzed citations for {os.path.basename(chapter_path)}")
            return citation_data
            
        except Exception as e:
            logger.error(f"Error analyzing chapter {chapter_path}: {e}")
            return None
            
    def _analyze_citations(self, text: str) -> Dict:
        """Analyze text for sentences requiring citations using Gemini.
        
        Args:
            text: Text content to analyze
            
        Returns:
            Dictionary containing citation analysis
        """
        prompt = """Analyze this thesis text and identify sentences that likely require citations.
        Focus on factual claims, established concepts, technical challenges, and specific examples.
        
        **IMPORTANT**: Do not include citations within mathematical equations or environments. 
        
        Respond with ONLY a valid JSON object in this exact format:
        {
            "sentences": [
                {
                    "sentence": "exact sentence from text",
                    "reason": "brief reason for citation",
                    "key_terms": ["term1", "term2"]
                }
            ]
        }
        """
        
        try:
            response = self.gemini_api.generate_content(prompt + "\n\nText:\n" + text)

            print(response)
            
            # Clean the response - remove any non-JSON content
            json_str = response.strip()
            if not json_str.startswith('{'):
                # Find the first { and last }
                start = json_str.find('{')
                end = json_str.rfind('}')
                if start >= 0 and end >= 0:
                    json_str = json_str[start:end+1]
                else:
                    raise ValueError("No JSON object found in response")
                    
            citation_data = json.loads(json_str)
            
            # Validate the structure
            if not isinstance(citation_data, dict) or "sentences" not in citation_data:
                raise ValueError("Invalid JSON structure")
                
            return citation_data
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse Gemini API response: {e}")
            return {"sentences": []}
        except Exception as e:
            logger.error(f"Error in citation analysis: {e}")
            return {"sentences": []}
            
    def _generate_citations(self, citation_data: Dict, max_results: int = 3) -> List[Dict]:
        """Generate citations for identified sentences.
        
        Args:
            citation_data: Citation analysis data
            max_results: Maximum number of papers per sentence
            
        Returns:
            List of paper details for citations
        """
        papers = []
        for idx, entry in enumerate(citation_data.get("sentences", [])):
            query = " ".join(entry["key_terms"]) + " [Title/Abstract]"
            logger.info(f"Querying PubMed for sentence {idx + 1}: '{query}'")
            
            pmids = self._search_pubmed(query, max_results)
            if not pmids:
                logger.warning(f"No results found for query: {query}")
                continue
                
            for pmid in pmids:
                paper = self._fetch_paper_details(pmid)
                if paper:
                    paper["sentence"] = entry["sentence"]  # Store the sentence for mapping
                    papers.append(paper)
                    logger.info(f"Added paper: {paper['title']} ({paper['year']})")
                time.sleep(0.5)  # Respect API rate limits
                
        return papers
        
    def _search_pubmed(self, query: str, max_results: int) -> List[str]:
        """Search PubMed for papers.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            List of PubMed IDs
        """
        try:
            handle = Entrez.esearch(db="pubmed", term=query, retmax=max_results, sort="relevance")
            record = Entrez.read(handle)
            handle.close()
            return record["IdList"]
        except Exception as e:
            logger.error(f"PubMed search error: {e}")
            return []
            
    def _fetch_paper_details(self, pmid: str) -> Optional[Dict]:
        """Fetch paper metadata from PubMed.
        
        Args:
            pmid: PubMed ID
            
        Returns:
            Dictionary containing paper details or None if fetch fails
        """
        try:
            handle = Entrez.efetch(db="pubmed", id=pmid, retmode="xml")
            record = Entrez.read(handle)
            handle.close()
            
            article = record["PubmedArticle"][0]["MedlineCitation"]["Article"]
            authors = [
                f"{a.get('LastName', '')}, {a.get('Initials', '')}"
                for a in article.get("AuthorList", [])
            ]
            
            return {
                "pmid": pmid,
                "title": article.get("ArticleTitle", "No title"),
                "authors": authors,
                "journal": article.get("Journal", {}).get("Title", "Unknown Journal"),
                "year": article.get("Journal", {}).get("JournalIssue", {}).get("PubDate", {}).get("Year", "Unknown"),
                "doi": next((id for id in record["PubmedArticle"][0].get("ArticleIdList", []) 
                           if id.attributes["IdType"] == "doi"), "Not available")
            }
        except Exception as e:
            logger.error(f"Error fetching PMID {pmid}: {e}")
            return None
            
    def _export_bibtex(self, papers: List[Dict], output_file: str) -> Dict[str, List[str]]:
        """Export paper details to BibTeX format and return citation keys.
        
        Args:
            papers: List of paper details
            output_file: Path to output BibTeX file
            
        Returns:
            Dictionary mapping sentences to lists of their citation keys
        """
        bibtex_entries = []
        citation_keys = {}
        
        for paper in papers:
            key = self._generate_bibtex_key(paper)
            entry = self._format_bibtex_entry(key, paper)
            bibtex_entries.append(entry)
            
            # Map the sentence to a list of citation keys
            if "sentence" in paper:
                if paper["sentence"] not in citation_keys:
                    citation_keys[paper["sentence"]] = []
                citation_keys[paper["sentence"]].append(key)
            
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n\n".join(bibtex_entries))
            
        logger.info(f"BibTeX entries saved to {output_file}")
        return citation_keys
            
    def _generate_bibtex_key(self, paper: Dict) -> str:
        """Generate unique BibTeX key for a paper.
        
        Args:
            paper: Paper details
            
        Returns:
            BibTeX key string
        """
        if paper["authors"]:
            first_author = paper["authors"][0].split(",")[0].lower()
            key = f"{first_author}{paper['year']}"
        else:
            key = f"pmid{paper['pmid']}{paper['year']}"
        return re.sub(r'[^a-z0-9]', '', key)
        
    def _format_bibtex_entry(self, key: str, paper: Dict) -> str:
        """Format paper details as BibTeX entry.
        
        Args:
            key: BibTeX citation key
            paper: Paper details
            
        Returns:
            Formatted BibTeX entry string
        """
        author_str = " and ".join([a.strip() for a in paper["authors"] if a.strip()]) or "Unknown Author"
        
        # Escape special characters in title and journal
        title = paper['title'].replace("&", "\\&")
        journal = paper['journal'].replace("&", "\\&")
        
        doi_field = f"  doi = {{{paper['doi']}}},\n" if paper['doi'] != "Not available" else ""
        
        return (f"@article{{{key},\n"
                f"  author = {{{author_str}}},\n"
                f"  title = {{{title}}},\n"
                f"  journal = {{{journal}}},\n"
                f"  year = {{{paper['year']}}},\n"
                f"{doi_field}"
                f"  pmid = {{{paper['pmid']}}}\n"
                f"}}")
                
    def _update_chapter_citations(self, chapter_path: str, citation_data: Dict, 
                                bibtex_keys: Dict[str, List[str]], debug_folder: str) -> None:
        """Update chapter markdown with citation references.
        
        Args:
            chapter_path: Path to chapter markdown file
            citation_data: Citation analysis data
            bibtex_keys: Mapping of sentences to lists of citation keys
            debug_folder: Path to debug folder
        """
        try:
            with open(chapter_path, "r", encoding="utf-8") as f:
                text = f.read()
                
            updated_text = text
            for entry in citation_data.get("sentences", []):
                sentence = entry["sentence"].strip()
                if sentence in bibtex_keys:
                    # Join multiple citation keys with semicolons
                    citations = "; ".join([f"@{key}" for key in bibtex_keys[sentence]])
                    citation = f"[{citations}]"
                    updated_text = re.sub(
                        f"{re.escape(sentence)}(?!\s*\[@)",
                        f"{sentence} {citation}",
                        updated_text,
                        count=1
                    )
                    
            # Save with consistent naming that matches thesis_compiler.py expectations
            chapter_name = os.path.basename(chapter_path).replace('_chapter.md', '')
            output_path = os.path.join(debug_folder, f"{chapter_name}_chapter_cited.md")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(updated_text)
                
            logger.info(f"Updated chapter saved to {output_path}")
            
        except Exception as e:
            logger.error(f"Error updating chapter citations for {chapter_path}: {e}")