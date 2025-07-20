import os
import logging
import time
import concurrent.futures
from typing import Dict, Optional, List
from ..ai.ai_api_interface import AIAPIInterface
from ..utils.style_manager import StyleManager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class YamlMetadataGenerator:
    """Generates YAML metadata for the thesis."""
    
    def __init__(self, ai_api: AIAPIInterface, style: str = 'thesis'):
        """Initialize the YamlMetadataGenerator.
        
        Args:
            ai_api: Instance of AIAPIInterface for metadata generation.
            style: Style name ('thesis' or 'nature').
        """
        self.ai_api = ai_api
        self.style = style
        self.style_config = StyleManager.get_style_config(style)
        
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

        metadata = self.ai_api.generate_content(metadata_prompt)
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
        
    def generate_english_abstract(self, chapters_content: Dict[str, str]) -> str:
        """Generate abstract from chapter contents.
        
        Args:
            chapters_content: Dictionary mapping chapter types to their content.
            
        Returns:
            Generated abstract text.
        """
        abstract_prompt = """You are an expert academic writer. Based on the thesis content provided below, write a concise abstract (250-300 words) in ONLY one paragraph\n.
        
        Thesis content:\n""" + "\n\n".join(chapters_content.values())

        abstract = self.ai_api.generate_content(abstract_prompt)
        return abstract if abstract else "Abstract generation failed."
        
    def generate_chinese_abstract(self, english_abstract: str) -> str:
        """Generate Traditional Chinese abstract from English abstract.
        
        Args:
            english_abstract: The English abstract to translate.
            
        Returns:
            Traditional Chinese abstract text.
        """
        chinese_prompt = f"""You are an expert academic translator specializing in Traditional Chinese. 
        Please translate the following English thesis abstract into Traditional Chinese, maintaining:

        1. Academic tone and formal writing style
        2. Technical terminology accuracy
        3. Proper Traditional Chinese academic conventions
        4. Same paragraph structure and content flow
        5. Appropriate length (250-300 words in Traditional Chinese) in one paragraph

        Please provide ONLY the Traditional Chinese translation, no additional commentary.

        English Abstract:
        {english_abstract}"""

        chinese_abstract = self.ai_api.generate_content(chinese_prompt)
        return chinese_abstract if chinese_abstract else "中文摘要生成失敗。"
        
    def generate_acknowledgements(self, advisor_name: str = None) -> str:
        """Generate Traditional Chinese acknowledgements.
        
        Args:
            advisor_name: Name of the advisor/professor
            
        Returns:
            Traditional Chinese acknowledgements text
        """
        advisor_info = ""
        if advisor_name:
            advisor_info = f"The advisor's name is: {advisor_name}. Please use this specific name when thanking the advisor."
        
        acknowledgements_prompt = f"""You are a world-class acknowledgements writer specializing in Traditional Chinese. 
        Write a heartfelt acknowledgements section (誌謝) in Traditional Chinese for a master student about to graduate.

        {advisor_info}

        The acknowledgements should:
        1. Express sincere gratitude to the advisor for guidance and support
        2. Thank family members for their support and understanding
        3. Acknowledge classmates, lab members, or colleagues who helped
        4. Thank the institution/university for providing resources
        5. Be approximately 200-300 words in Traditional Chinese
        6. Use heartfelt and touching tone
        7. You may include some mentions of research guidance, personal growth, and friendship development.

        Please write ONLY the acknowledgements content in Traditional Chinese, without any title or additional commentary.
        The text should be suitable for direct inclusion in a thesis document."""

        acknowledgements = self.ai_api.generate_content(acknowledgements_prompt)
        return acknowledgements if acknowledgements else "感謝指導教授的悉心指導，以及家人朋友的支持與鼓勵。"
        
    def generate_metadata(self, chapters_dir: str, output_file: str) -> bool:
        """Generate YAML metadata from chapter files.
        
        Args:
            chapters_dir: Directory containing chapter files.
            output_file: Path to write the YAML metadata file.
            
        Returns:
            True if metadata generation succeeds, False otherwise.
        """
        # Route to appropriate metadata generation method
        if self.style == 'nature':
            return self._generate_nature_metadata(chapters_dir, output_file)
        else:
            return self._generate_thesis_metadata(chapters_dir, output_file)
    
    def _generate_thesis_metadata(self, chapters_dir: str, output_file: str) -> bool:
        """Generate thesis metadata (original implementation).
        
        Args:
            chapters_dir: Directory containing chapter files.
            output_file: Path to write the YAML metadata file.
            
        Returns:
            True if metadata generation succeeds, False otherwise.
        """
        try:
            # Read chapter contents
            chapters_content = {}
            chapter_order = ['introduction', 'methods', 'results', 'conclusions']
            
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
            
            # First extract metadata to get advisor name
            metadata = self.extract_metadata_from_intro(intro_content)
            logger.debug(metadata)
            
            # Run acknowledgements and abstract generation in parallel, using the extracted advisor name
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                # Submit tasks
                acknowledgements_future = executor.submit(self.generate_acknowledgements, metadata.get('advisor'))
                abstract_future = executor.submit(self.generate_english_abstract, chapters_content)
                
                # Get results
                acknowledgements = acknowledgements_future.result()
                logger.info("Generated Chinese acknowledgements")
                logger.debug(acknowledgements)
                
                abstract = abstract_future.result()
                logger.info("Generated English abstract")
                logger.debug(abstract)
            
            # Generate Chinese abstract (depends on English abstract, so run after)
            chinese_abstract = self.generate_chinese_abstract(abstract)
            logger.info("Generated Traditional Chinese abstract")
            logger.debug(chinese_abstract)
            
                        
            # Create YAML content - only include settings relevant to custom template
            yaml_template = "---\n"
            yaml_template += f'title: "{metadata["title"]}"\n'
            yaml_template += f'author: "{metadata["author"]}"\n'
            if metadata.get('advisor'):
                yaml_template += f'supervisor: "{metadata["advisor"]}"\n'  # Map advisor to supervisor for template
            yaml_template += f'date: "{time.strftime("%Y-%m-%d")}"\n'

            # table of contents will be broken if not set. strange.
            yaml_template += "documentclass: report\n"
            yaml_template += "toc: true\n"
            yaml_template += "toc-depth: 2\n"

            # Add pandoc-crossref settings (these are still needed)
            yaml_template += "figPrefix: Figure\n"
            yaml_template += "eqnPrefix: Equation\n"
            yaml_template += "tblPrefix: Table\n"
            yaml_template += "secPrefix: Section\n"
            yaml_template += "linkReferences: true\n"

            # Add English abstract
            yaml_template += "abstract: |\n"
            for line in abstract.strip().split('\n'):
                yaml_template += f"  {line}\n"
            
            # Add Chinese abstract
            yaml_template += "abstract-zh: |\n"
            for line in chinese_abstract.strip().split('\n'):
                yaml_template += f"  {line}\n"
            
            # Add Chinese acknowledgements
            yaml_template += "acknowledgements-zh: |\n"
            for line in acknowledgements.strip().split('\n'):
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
    
    def _generate_nature_metadata(self, chapters_dir: str, output_file: str) -> bool:
        """Generate Nature journal metadata.
        
        Args:
            chapters_dir: Directory containing chapter files.
            output_file: Path to write the YAML metadata file.
            
        Returns:
            True if metadata generation succeeds, False otherwise.
        """
        try:
            # Read chapter contents
            chapters_content = {}
            chapter_order = ['introduction', 'methods', 'results', 'conclusions']
            
            for chapter_type in chapter_order:
                chapter_file = os.path.join(chapters_dir, f"{chapter_type.lower().replace(' ', '_')}_chapter_cited.md")
                if os.path.exists(chapter_file):
                    with open(chapter_file, 'r', encoding='utf-8') as f:
                        chapters_content[chapter_type] = f.read()
                        
            if not chapters_content:
                logger.error("No chapter files found")
                return False
                
            # Extract metadata from introduction
            intro_file = os.path.join(chapters_dir, "introduction_section.txt")
            intro_content = ""
            if os.path.exists(intro_file):
                with open(intro_file, 'r', encoding='utf-8') as f:
                    intro_content = f.read()
            
            # Run metadata extraction and abstract generation in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                metadata_future = executor.submit(self.extract_metadata_from_intro, intro_content)
                abstract_future = executor.submit(self.generate_english_abstract, chapters_content)
                
                metadata = metadata_future.result()
                logger.debug(metadata)
                
                abstract = abstract_future.result()
                logger.info("Generated English abstract")
                logger.debug(abstract)
            
            # Create Nature journal YAML content
            yaml_template = "---\n"
            yaml_template += f'title: "{metadata["title"]}"\n'
            
            # Nature journal author format
            yaml_template += "authors:\n"
            yaml_template += f'  - given_name: "{metadata["author"].split()[0] if metadata["author"] else "First"}"\n'
            yaml_template += f'    family_name: "{" ".join(metadata["author"].split()[1:]) if len(metadata["author"].split()) > 1 else "Author"}"\n'
            yaml_template += f'    email: "author@example.com"\n'
            
            # Affiliations
            yaml_template += "affiliations:\n"
            yaml_template += "  - department: \"Department\"\n"
            yaml_template += "    organization: \"Institution\"\n"
            
            # Abstract for Nature (single paragraph)
            yaml_template += "abstract: |\n"
            # Ensure single paragraph by replacing newlines with spaces
            clean_abstract = " ".join(abstract.strip().replace('\n', ' ').split())
            yaml_template += f"  {clean_abstract}\n"
            
            # Keywords (simplified)
            yaml_template += "keywords: \"research, analysis, methodology\"\n"
            
            # Document class settings
            yaml_template += "documentclass: sn-jnl\n"
            yaml_template += "classoption: [pdflatex, sn-nature]\n"
            yaml_template += "bibliography: references\n"
            yaml_template += "biblio-style: sn-nature\n"
            
            yaml_template += "---\n"
            
            # Save the YAML content
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(yaml_template)
                
            logger.info(f"Generated Nature journal YAML metadata: {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error generating Nature metadata: {e}")
            return False 