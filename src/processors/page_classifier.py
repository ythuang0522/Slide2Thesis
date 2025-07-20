import os
import logging
import re
from typing import Dict, Optional
from ..ai.ai_api_interface import AIAPIInterface

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PageClassifier:
    """Classifies extracted pages into thesis sections."""
    
    def __init__(self, ai_api: AIAPIInterface):
        """Initialize the PageClassifier.
        
        Args:
            ai_api: Instance of AIAPIInterface for text classification.
        """
        self.ai_api = ai_api
        self.categories = ['introduction', 'related works', 'methods', 'results', 'conclusions', 'appendix']
        
    def load_extracted_text(self, text_file_path: str) -> Optional[Dict[str, str]]:
        """Load extracted text from file into a dictionary.
        
        Args:
            text_file_path: Path to the extracted text file.
            
        Returns:
            Dictionary with page numbers as keys and text as values, or None if loading fails.
        """
        try:
            extracted_data = {}
            current_page, current_text = None, []
            page_pattern = re.compile(r'\*Page \d+\*:')
            
            with open(text_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if page_pattern.match(line.strip()):
                        if current_page and current_text:
                            extracted_data[current_page] = ''.join(current_text)
                        current_page = line.strip().rstrip(':')
                        current_text = []
                    elif current_page:
                        current_text.append(line)
                        
            if current_page and current_text:
                extracted_data[current_page] = ''.join(current_text)
                
            return extracted_data if extracted_data else None
            
        except Exception as e:
            logger.error(f"Error loading {text_file_path}: {e}")
            return None
            
    def _create_classification_prompt(self, extracted_data: Dict[str, str]) -> str:
        """Create the prompt for the AI API classification.
        
        This method constructs a detailed prompt that instructs the AI model how to classify
        academic presentation pages. It includes:
        - The classification task description
        - Expected output format
        - Classification guidelines
        - The actual content to be classified
        
        Args:
            extracted_data: Dictionary mapping page identifiers to their text content
                          Format: {'Page 1': 'content', '*Page 2*': 'content', ...}
        
        Returns:
            A formatted string containing the complete classification prompt
        """
        base_prompt = """You are an expert in categorizing content from academic presentations. Analyze these pages and classify each page number into one of these categories: Introduction, Related Works, Methods, Results, Conclusions, Appendix, and Unrelated.

        Return ONLY the page numbers for each category in this format:
        Introduction: [page numbers]
        Related Works: [page numbers]
        Methods: [page numbers]
        Results: [page numbers]
        Conclusions: [page numbers]
        Appendix: [page numbers]
        Unrelated: [page numbers]

        Consider:
        1. Pages of the same category typically have continuous page numbers. The classification is like partitioning the pages into categories.
        2. Each page must be classified into exactly one category
        3. If uncertain, classify with adjacent pages' category (e.g., if the page is between two pages of the Methods category, classify it as the Methods category)
        4. If the page is clearly unrelated to any category (e.g., a thank you slide), classify it as Unrelated. No that the slides in the middle must not be classified as Unrelated.
        
        Pages to analyze:
        """
        
        for page_num, content in extracted_data.items():
            base_prompt += f"\n{page_num}:\n{content}\n"
        return base_prompt

    def _get_target_pages(self, classification_result: str, category: str) -> list:
        """Extract page numbers for a specific category from the API classification result.
        
        Parses the API response to find all page numbers associated with a given category.
        For example, from a line like "Introduction: 1, 2, 3", it extracts [1, 2, 3].
        
        Args:
            classification_result: The complete classification response from the API
            category: The category to extract pages for (e.g., 'introduction', 'methods')
        
        Returns:
            List of page numbers (as strings) belonging to the specified category
        """
        target_pages = []
        for line in classification_result.split('\n'):
            if line.lower().startswith(category.lower()):
                numbers = re.findall(r'\d+', line)
                target_pages.extend(numbers)
        return target_pages

    def _get_page_content(self, page_num: str, extracted_data: Dict[str, str]) -> Optional[str]:
        """Retrieve the content for a specific page number.
        
        Handles different possible formats of page keys in the extracted data.
        For example, page 1 might be stored under keys like:
        - "Page 1"
        - "*Page 1*"
        - "Page 1:"
        
        Args:
            page_num: The page number to look up
            extracted_data: Dictionary containing all page contents
        
        Returns:
            The page content if found, None otherwise
        """
        possible_keys = [
            f"Page {page_num}",
            f"*Page {page_num}*",
            f"Page {page_num}:",
        ]
        
        for key in possible_keys:
            if str(key) in extracted_data:
                return extracted_data[str(key)]
        return None

    def _write_category_content(self, category: str, content: str, output_dir: str) -> None:
        """Write the categorized content to a file in the output directory.
        
        Creates a file named after the category (e.g., "introduction_section.txt")
        and writes all content for that category to it.
        
        Args:
            category: The category name (e.g., 'introduction', 'methods')
            content: The complete text content for this category
            output_dir: Directory path where the file should be created
        """
        output_file = os.path.join(output_dir, f"{category.lower().replace(' ', '_')}_section.txt")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)

    def classify_pages(self, extracted_text_file: str, output_dir: str) -> Dict[str, str]:
        """Main method to classify pages and organize them into sections.
        
        This method orchestrates the complete classification process:
        1. Loads the extracted text from the input file
        2. Creates and sends a classification prompt to the AI API
        3. Processes the API response to organize pages by category
        4. Writes each category's content to separate files
        5. Returns the organized content
        
        The process handles several edge cases:
        - Missing or empty input file
        - Failed API responses
        - Pages mentioned in classification but not found in data
        
        Args:
            extracted_text_file: Path to the file containing all extracted page text
            output_dir: Directory where categorized section files will be written
        
        Returns:
            Dictionary mapping categories to their compiled content
            Format: {'introduction': 'content...', 'methods': 'content...', ...}
            Returns empty dict if classification fails
        """
        extracted_data = self.load_extracted_text(extracted_text_file)
        if not extracted_data:
            logger.error("No extracted text data to classify")
            return {}
            
        # Get classification from API
        classification_prompt = self._create_classification_prompt(extracted_data)
        classification_result = self.ai_api.generate_content(classification_prompt)
        if not classification_result:
            logger.error("No classification result received from API")
            return {}
            
        logger.debug("Classification result: %s", classification_result)

        # Process each category
        categorized_content = {}
        for category in self.categories:
            target_pages = self._get_target_pages(classification_result, category)
            
            # Collect content for this category's pages
            category_content = []
            for page_num in sorted(target_pages, key=int):
                page_content = self._get_page_content(page_num, extracted_data)
                
                if page_content:
                    category_content.append(f"Page {page_num}:\n{page_content}\n")
                else:
                    logger.warning(f"Page {page_num} not found in extracted data")
                    
            if category_content:
                categorized_content[category] = "\n\n".join(category_content)
                self._write_category_content(category, categorized_content[category], output_dir)
                    
        return categorized_content 