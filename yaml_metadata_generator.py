import os
import logging
import time
from typing import Dict, Optional, List
from gemini_api import GeminiAPI

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class YamlMetadataGenerator:
    """Generates YAML metadata for the thesis."""
    
    def __init__(self, gemini_api: GeminiAPI):
        """Initialize the YamlMetadataGenerator.
        
        Args:
            gemini_api: Instance of GeminiAPI for metadata generation.
        """
        self.gemini_api = gemini_api
        
    def extract_metadata_from_intro(self, intro_content: str) -> Dict[str, str]:
        """Extract title, author, and advisor from introduction content.
        
        Args:
            intro_content: Content of the introduction chapter.
            
        Returns:
            Dictionary containing title, author, and advisor.
        """
        metadata_prompt = """From the following thesis introduction text, please extract:
        1. The thesis title
        2. The author's name
        3. The advisor's name (if present)
        
        Note that these information are usually at the first page. Return only these three pieces of information, one per line.
        
        Text:
        """ + intro_content

        metadata = self.gemini_api.generate_content(metadata_prompt)
        result = {
            'title': "Thesis Title",
            'author': "Author Name",
            'advisor': None
        }

        if metadata:
            metadata_lines = metadata.strip().split('\n')
            if len(metadata_lines) >= 1:
                result['title'] = metadata_lines[0].strip()
            if len(metadata_lines) >= 2:
                result['author'] = metadata_lines[1].strip()
            if len(metadata_lines) >= 3:
                result['advisor'] = metadata_lines[2].strip()
                
        return result
        
    def generate_abstract(self, chapters_content: Dict[str, str]) -> str:
        """Generate abstract from chapter contents.
        
        Args:
            chapters_content: Dictionary mapping chapter types to their content.
            
        Returns:
            Generated abstract text.
        """
        abstract_prompt = """You are an expert academic writer. Based on the thesis content provided below, write a concise abstract (250-300 words) in ONLY one paragraph\n.
        
        Thesis content:\n""" + "\n\n".join(chapters_content.values())

        abstract = self.gemini_api.generate_content(abstract_prompt)
        return abstract if abstract else "Abstract generation failed."
        
    def generate_metadata(self, chapters_dir: str, output_file: str) -> bool:
        """Generate YAML metadata from chapter files.
        
        Args:
            chapters_dir: Directory containing chapter files.
            output_file: Path to write the YAML metadata file.
            
        Returns:
            True if metadata generation succeeds, False otherwise.
        """
        try:
            # Read chapter contents
            chapters_content = {}
            chapter_order = ['introduction', 'related works', 'methods', 'results', 'conclusions', 'appendix']
            
            for chapter_type in chapter_order:
                chapter_file = os.path.join(chapters_dir, f"{chapter_type.lower().replace(' ', '_')}_chapter_cited.md")
                if os.path.exists(chapter_file):
                    with open(chapter_file, 'r', encoding='utf-8') as f:
                        chapters_content[chapter_type] = f.read()
                        
            if not chapters_content:
                logger.error("No chapter files found")
                return False
                
            # Extract metadata from introduction
            # Read introduction from introduction_section.txt
            intro_file = os.path.join(chapters_dir, "introduction_section.txt")
            intro_content = ""
            if os.path.exists(intro_file):
                with open(intro_file, 'r', encoding='utf-8') as f:
                    intro_content = f.read()
            
            metadata = self.extract_metadata_from_intro(intro_content)
            print(metadata)
            
            # Generate abstract
            abstract = self.generate_abstract(chapters_content)
            print(abstract)
            
            # Create YAML content
            yaml_template = "---\n"
            yaml_template += f'title: "{metadata["title"]}"\n'
            yaml_template += f'author: "{metadata["author"]}"\n'
            if metadata.get('advisor'):
                yaml_template += f'advisor: "{metadata["advisor"]}"\n'
            yaml_template += f'date: "{time.strftime("%Y-%m-%d")}"\n'
            yaml_template += "documentclass: report\n"
            yaml_template += "toc: true\n"
            yaml_template += "toc-depth: 2\n"

            # Add pandoc-crossref settings
            yaml_template += "figPrefix: \n"
            yaml_template += "eqnPrefix: Equation\n"
            yaml_template += "tblPrefix: Table\n"
            yaml_template += "secPrefix: Section\n"
            yaml_template += "linkReferences: true\n"
            

            yaml_template += "abstract: |\n"
            
            # Add each line of the abstract with proper indentation
            for line in abstract.strip().split('\n'):
                yaml_template += f"  {line}\n"
            yaml_template += "---\n"
            
            # Save the YAML content
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(yaml_template)
                
            logger.info(f"Generated YAML metadata: {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error generating YAML metadata: {e}")
            return False 