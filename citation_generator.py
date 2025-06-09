import json
import re
import os
import logging
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from Bio import Entrez
import time
from ai_api_interface import AIAPIInterface

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CitationGenerator:
    """Generates and manages citations for thesis chapters."""
    
    def __init__(self, ai_api: AIAPIInterface, email: str):
        """Initialize the CitationGenerator.
        
        Args:
            ai_api: Instance of AIAPIInterface for citation analysis
            email: Email for PubMed API access
        """
        self.ai_api = ai_api
        Entrez.email = email
        
    def process_chapters(self, debug_folder: str, threads: int = 1) -> bool:
        """Process all chapter files in the debug folder and add citations.
        
        Args:
            debug_folder: Path to the debug folder containing chapter files
            threads: Number of threads to use for concurrent processing (default: 1)
            
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
            
            if threads <= 1:
                # Sequential processing (original behavior)
                logger.info("Processing chapters sequentially for citations...")
                for chapter_file in chapter_files:
                    chapter_file_result, citation_data, papers = self._process_single_chapter_task(
                        chapter_file, debug_folder, citation_chapters
                    )
                    if citation_data:
                        citation_data_by_chapter[chapter_file_result] = citation_data
                        all_papers.extend(papers)
            else:
                # Concurrent processing
                logger.info(f"Processing chapters concurrently for citations using {threads} threads...")
                with ThreadPoolExecutor(max_workers=threads) as executor:
                    # Submit all chapter processing tasks
                    future_to_chapter = {
                        executor.submit(self._process_single_chapter_task, chapter_file, debug_folder, citation_chapters): chapter_file
                        for chapter_file in chapter_files
                    }
                    
                    # Collect results as they complete
                    for future in as_completed(future_to_chapter):
                        chapter_file = future_to_chapter[future]
                        try:
                            chapter_file_result, citation_data, papers = future.result()
                            if citation_data:
                                citation_data_by_chapter[chapter_file_result] = citation_data
                                all_papers.extend(papers)
                                logger.info(f"Completed citation processing for {chapter_file_result}")
                        except Exception as e:
                            logger.error(f"Error processing citations for {chapter_file}: {str(e)}")
            
            if not all_papers:
                logger.warning("No citations were generated for any chapter")
                return False
                
            # Export all citations to BibTeX
            bibtex_file = os.path.join(debug_folder, "references.bib")
            bibtex_keys = self._export_bibtex(all_papers, bibtex_file)
            
            # Update each chapter with its corresponding citations
            # This loop iterates through each chapter and its citation data
            # For each chapter, it:
            # 1. Constructs the full path to the chapter file
            # 2. Calls _update_chapter_citations to add citation references
            # 3. The citations are added in the format [@citation_key]
            # 4. The updated chapter is saved with a new filename in the debug folder
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
            logger.info(f"Analyzed citations for {os.path.basename(chapter_path)}")
            return citation_data
            
        except Exception as e:
            logger.error(f"Error analyzing chapter {chapter_path}: {e}")
            return None
            
    def _analyze_citations(self, text: str) -> Dict:
        """Analyze text for sentences requiring citations using AIAPI.
        
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
            response = self.ai_api.generate_content(prompt + "\n\nText:\n" + text)

            logger.debug(response)
            
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
            logger.error(f"Failed to parse AIAPI response: {e}")
            return {"sentences": []}
        except Exception as e:
            logger.error(f"Error in citation analysis: {e}")
            return {"sentences": []}
    
    def _process_single_chapter_task(self, chapter_file: str, debug_folder: str, citation_chapters: List[str]) -> tuple[str, Optional[Dict], List[Dict]]:
        """Process a single chapter for citations (for concurrent execution).
        
        Args:
            chapter_file: Name of the chapter file
            debug_folder: Path to the debug folder
            citation_chapters: List of chapters that need citations
            
        Returns:
            Tuple of (chapter_file, citation_data, papers)
        """
        chapter_path = os.path.join(debug_folder, chapter_file)
        chapter_name = chapter_file.replace('_chapter.md', '')
        
        # Only process citations for specific chapters
        if chapter_name in citation_chapters:
            logger.info(f"Processing citations for {chapter_file}")
            
            # Analyze chapter for citations
            citation_data = self._analyze_chapter(chapter_path)
            if citation_data:
                # Generate citations
                papers = self._generate_citations(citation_data)
                return chapter_file, citation_data, papers
            else:
                return chapter_file, None, []
        else:
            # For non-citation chapters, just create the _cited version without modifications
            base_name = os.path.splitext(os.path.basename(chapter_path))[0]
            output_path = os.path.join(debug_folder, f"{base_name}_cited.md")
            with open(chapter_path, "r", encoding="utf-8") as f:
                text = f.read()
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(text)
            logger.info(f"Created cited version without citations for {chapter_file}")
            return chapter_file, None, []
    
    def _generate_citations_for_sentence(self, entry: Dict, max_results: int = 3) -> List[Dict]:
        """Generate citations for a single sentence (for concurrent execution).
        
        Args:
            entry: Citation entry containing sentence and key terms
            max_results: Maximum number of papers per sentence
            
        Returns:
            List of paper details for this sentence
        """
        papers = []
        query = " ".join(entry["key_terms"]) + " [Title/Abstract]"
        logger.info(f"Querying PubMed for sentence: '{query}'")
        
        pmids = self._search_pubmed(query, max_results)
        if not pmids:
            logger.warning(f"No results found for query: {query}")
            return papers
            
        for pmid in pmids:
            paper = self._fetch_paper_details(pmid)
            if paper:
                paper["sentence"] = entry["sentence"]  # Store the sentence for mapping
                papers.append(paper)
                logger.info(f"Added paper: {paper['title']} ({paper['year']})")
            time.sleep(0.5)  # Respect API rate limits
            
        return papers
            
    def _generate_citations(self, citation_data: Dict, max_results: int = 3) -> List[Dict]:
        """Generate citations for identified sentences.
        
        Args:
            citation_data: Citation analysis data
            max_results: Maximum number of papers per sentence
            
        Returns:
            List of paper details for citations
        """
        papers = []
        sentences = citation_data.get("sentences", [])
        
        if not sentences:
            return papers
            
        # For citation generation, we use sequential processing to respect PubMed API rate limits
        # Concurrent requests to PubMed could cause rate limiting issues
        for idx, entry in enumerate(sentences):
            logger.info(f"Processing sentence {idx + 1} of {len(sentences)}")
            sentence_papers = self._generate_citations_for_sentence(entry, max_results)
            papers.extend(sentence_papers)
                
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
            from Bio import Medline
            handle = Entrez.efetch(db="pubmed", id=pmid, rettype="medline", retmode="text")
            records = list(Medline.parse(handle))
            handle.close()
            
            if not records:
                logger.warning(f"No records found for PMID {pmid}")
                return None
                
            record = records[0]  # Get the first record
            
            # Extract authors in "LastName, Initials" format
            authors = []
            if "AU" in record:
                for author in record.get("AU", []):
                    # Authors in Medline format are already "LastName Initials"
                    # Convert to "LastName, Initials" format
                    parts = author.split()
                    if len(parts) > 1:
                        lastname = parts[0]
                        initials = " ".join(parts[1:])
                        authors.append(f"{lastname}, {initials}")
                    else:
                        authors.append(author)
            
            # Get publication year from the date
            year = "Unknown"
            if "DP" in record:
                # Date format is typically "YYYY Mon DD" or "YYYY"
                date_parts = record.get("DP", "").split()
                if date_parts and date_parts[0].isdigit():
                    year = date_parts[0]
            
            # Get DOI if available
            doi = "Not available"
            if "LID" in record:
                lid = record.get("LID", "")
                if "[doi]" in lid:
                    doi = lid.split(" [doi]")[0]
            elif "AID" in record:
                for aid in record.get("AID", []):
                    if "[doi]" in aid:
                        doi = aid.split(" [doi]")[0]
                        break
            
            return {
                "pmid": pmid,
                "title": record.get("TI", "No title"),
                "authors": authors,
                "journal": record.get("TA", "Unknown Journal"),
                "year": year,
                "doi": doi
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
        used_keys = set()  # Track used keys to prevent duplicates
        
        for paper in papers:
            key = self._generate_bibtex_key(paper)
            
            # Ensure key is unique
            base_key = key
            counter = 1
            while key in used_keys:
                key = f"{base_key}{counter}"
                counter += 1
            
            used_keys.add(key)
            
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
            # Get first author's last name
            first_author = paper["authors"][0].split(",")[0].lower()
            
            # Normalize to ASCII - replace accented characters with ASCII equivalents
            import unicodedata
            first_author = unicodedata.normalize('NFKD', first_author)
            first_author = ''.join([c for c in first_author if not unicodedata.combining(c)])
            
            key = f"{first_author}{paper['year']}"
        else:
            key = f"pmid{paper['pmid']}{paper['year']}"
            
        # Ensure key only contains valid characters
        return re.sub(r'[^a-z0-9]', '', key)
        
    def _format_bibtex_entry(self, key: str, paper: Dict) -> str:
        """Format paper details as BibTeX entry.
        
        Args:
            key: BibTeX citation key
            paper: Paper details
            
        Returns:
            Formatted BibTeX entry string
        """
        # Handle author list - limit to 5 authors for very long lists
        authors = [a.strip() for a in paper["authors"] if a.strip()]
        if len(authors) > 10:
            author_str = " and ".join(authors[:5]) + " and others"
        else:
            author_str = " and ".join(authors) or "Unknown Author"
        
        # Remove HTML/XML tags from title
        title = re.sub(r'<[^>]+>', '', paper['title'])
        
        # Escape special characters in title and journal (backslash must be first!)
        title = (title.replace("\\", "\\textbackslash")
                     .replace("&", "\\&")
                     .replace("%", "\\%")
                     .replace("$", "\\$")
                     .replace("#", "\\#")
                     .replace("_", "\\_")
                     .replace("{", "\\{")
                     .replace("}", "\\}")
                     .replace("~", "\\textasciitilde")
                     .replace("^", "\\textasciicircum"))
        
        journal = (paper['journal'].replace("\\", "\\textbackslash")
                                   .replace("&", "\\&")
                                   .replace("%", "\\%")
                                   .replace("$", "\\$")
                                   .replace("#", "\\#")
                                   .replace("_", "\\_")
                                   .replace("{", "\\{")
                                   .replace("}", "\\}"))
        
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
                    
                    # Check if sentence ends with punctuation (period, comma, or semicolon)
                    punctuation_marks = ['.', ',', ';']
                    ending_punctuation = None
                    
                    for punct in punctuation_marks:
                        if sentence.endswith(punct):
                            ending_punctuation = punct
                            break
                    
                    if ending_punctuation:
                        # Insert citation before the punctuation with non-breaking space
                        sentence_without_punct = sentence[:-1]
                        escaped_punct = re.escape(ending_punctuation)
                        updated_text = re.sub(
                            f"{re.escape(sentence_without_punct)}{escaped_punct}(?!\\s*\\[@)",
                            f"{sentence_without_punct}&nbsp;{citation}{ending_punctuation}",
                            updated_text,
                            count=1
                        )
                    else:
                        # For sentences without punctuation, add citation at the end with non-breaking space
                        updated_text = re.sub(
                            f"{re.escape(sentence)}(?!\\s*\\[@)",
                            f"{sentence}&nbsp;{citation}",
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