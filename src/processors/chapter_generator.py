import os
import logging
from typing import Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from ..ai.ai_api_interface import AIAPIInterface

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ChapterGenerator:
    """Generates thesis chapters from classified sections."""
    
    def __init__(self, ai_api: AIAPIInterface):
        """Initialize the ChapterGenerator.
        
        Args:
            ai_api: Instance of AIAPIInterface for chapter generation.
        """
        self.ai_api = ai_api
        self.categories = ['introduction', 'related works', 'methods', 'results', 'conclusions', 'appendix']
        
    def generate_chapter(self, section_content: str, chapter_type: str) -> Optional[str]:
        """Generate a single chapter from section content.
        
        Args:
            section_content: Content of the section.
            chapter_type: Type of chapter ('introduction', 'methods', etc.).
            
        Returns:
            Generated chapter text or None if generation fails.
        """
        # Define general thesis chapter guidelines
        general_guidelines = """You are an expert academic writer tasked with composing a world-class thesis chapter. You are provided with a set of page contents relevant to this {chapter_type} chapter. Your job is to integrate, refine, and expand on this material to create a polished, coherent, and comprehensive chapter that meets high thesis standards.

        Please follow these general guidelines:
        1. Carefully review all provided page contents and write a world-class thesis for this {chapter_type} chapter.
        2. If necessary, fill in gaps with logical transitions or additional information that strengthens the chapter's narrative.
        3. **Organize the chapter using markdown format** into clearly defined sections and, if applicable, subheadings that reflect its purpose. 
        4. Do NOT include explicit chapter or section numbers in your markdown headers (e.g., use "## Overview" instead of "## 3.1 Overview"). LaTeX will automatically number all sections.
        5. Whenever outputting mathematical equations, remember to wrap them with a single pair of dollar signs for inline equations and a double pair for displayed equations.
        6. Ensure the chapter follows a logical progression that guides the reader through the main points effectively.
        7. Academic Tone and Rigor: Write in a formal, objective, and precise academic style suitable for a graduate-level thesis. 
        8. Don't include any source information (e.g., page numbers, slides, figure numbers, etc.) and figure reference links.
        9. Always start the markdown with a chapter title (e.g., # Introduction, # Related Works, # Methods, # Results, # Conclusions, # Appendix)
        """

        # Define chapter-specific guidelines
        specific_guidelines = {
            'introduction': """Chapter-Specific guidelines: 
            - Provides comprehensive background information necessary for understanding the the research problem
            - Keywords and background knowledge in the provided page contents must be introduced in this chapter.
            - Expand the background knowledge required to understand the keywords and research problem using your knowledge base. Don't limited to the provided page contents.
            - Comprehensively describe the importance, impact, and current challenges or limitations of the research problem.
            - This chapter should be ended with a concise statement of the research problem and the goal of the thesis.
            - Write 5-6 paragraphs for the introduction chapter""",
            
            'related works': """Chapter-Specific guidelines:
            - Introduces related works and literature review and their limitations from the provided page contents
            - Expand the related works and literature review using your knowledge base. Don't limited to the provided page contents
            - Write 3-4 paragraphs for the related works chapter""",

            'methods': """Chapter-Specific guidelines:
            - Don't miss any details in each page content. Write each part as detailed as possible and expand the details using your knowledge base.""",

            'results': """Chapter-Specific guidelines:
            - Present each result page as detailed as possible. Remember to summarize the key messages of the results at the end of the paragraph or section.
            - If a result page contains a figure, describe the figure like a the main body of a scientific paper.
            - If a result page contains a table, describe the table like a the main body of a scientific paper.
            - You can fill in the details of the results using your knowledge base.""",

            'conclusions': """Chapter-Specific Considerations:
            - This is the ending chapter of the thesis. Briefly summarize the main findings, interpretations of the results, implications of the research, and potential future directions.
            - Write 3-4 paragraphs for the conclusions chapter.
            - You can fill in the details of the conclusions using your knowledge base.""",

            'appendix': """Chapter-Specific Considerations:
            - This is appendix of the thesis which includes supplementary information from pages after the conclusion. 
            - If the page contains a figure, write a complete figure legend explaining the figure.
            - If the page contains a table, write a complete table legend explaining the table. Formulate the tables in markdown format."""
        }

        prompt = (f"{general_guidelines}\n\n{specific_guidelines.get(chapter_type, '')}"
                f"\n\nBelow are the extracted text pages for the {chapter_type} chapter:\n\n{section_content}\n\nPlease generate a comprehensive {chapter_type} chapter based on above guidelines and content.")
        
        return self.ai_api.generate_content(prompt)
        
    def check_and_expand_chapter(self, section_content: str, chapter_text: str) -> str:
        """Check for missing content and expand if necessary.
        
        Args:
            section_content: Original content from the section file.
            chapter_text: Generated chapter text.
            
        Returns:
            Expanded chapter text including any missing content.
        """
        prompt = """You are an expert academic writer. Compare the original contents and the generated chapter text below. 
        Your task is to:
        1. Identify any content from the original contents that is missing in the generated chapter text
        2. If any missing content is found, expand the generated chapter text to include this missing content while maintaining the original flow and academic writing style
        3. The newly expanded chapter content should follow the original markdown format of the generated chapter text.
        4. Return the expanded chapter text in markdown format
        
        **Original contents:**
        {section_content}
        
        **Generated chapter text:**
        {chapter_text}
        """
        
        expanded_text = self.ai_api.generate_content(prompt.format(
            section_content=section_content,
            chapter_text=chapter_text
        ))
        
        return expanded_text if expanded_text else chapter_text
        
    def polish_thesis_content(self, chapter_text: str) -> str:
        """Polish thesis chapter content.
        
        Args:
            chapter_text: The chapter text to polish.
            
        Returns:
            Polished chapter text.
        """
        prompt = """You are an expert academic thesis editor. Polish the following thesis chapter to meet the highest academic standards.

        Guidelines:
        1. Convert any slide-based language into professional thesis writing
        2. Ensure consistent academic tone throughout
        3. Maintain all technical content, equations, and important information
        4. Keep the same markdown formatting structure
        5. Preserve all section headings but **REMOVE any explicit chapter or section numbers** (e.g., change "## 3.1 Overview" to "## Overview")
        6. Keep equations in LaTeX format ($ for inline, $$ for display)
        7. Ensure the writing flows naturally between sections
        8. Remove apparent editing artifacts (e.g., "Here's the expanded chapter text")

        Return the polished chapter text in markdown format.

        Chapter content to polish:
        {chapter_text}"""

        polished_text = self.ai_api.generate_content(prompt.format(chapter_text=chapter_text))
        
        # Clean up any remaining markdown code block markers
        if polished_text:
            polished_text = polished_text.replace('```markdown\n', '').replace('```', '').strip()
        
        # Apply math formatting as final step
        try:
            from ..utils.math_formatter import MathFormatter
            math_formatter = MathFormatter()
            polished_text = math_formatter.format_content(polished_text)
            logger.debug("Applied math formatting to chapter content")
        except Exception as e:
            logger.warning(f"Math formatting failed: {e}")
            # Continue without math formatting if it fails
        
        return polished_text if polished_text else chapter_text
    
    def _generate_single_chapter_task(self, category: str, working_dir: str) -> tuple[str, Optional[str]]:
        """Generate a single chapter task for concurrent execution.
        
        Args:
            category: Chapter category to generate.
            working_dir: Directory containing section files.
            
        Returns:
            Tuple of (category, generated_chapter_content) or (category, None) if failed.
        """
        section_file = os.path.join(working_dir, f"{category.lower().replace(' ', '_')}_section.txt")
        if not os.path.exists(section_file):
            logger.info(f"Skipping {category} - section file not found")
            return category, None
            
        # Read the content and check if it's empty
        with open(section_file, 'r', encoding='utf-8') as f:
            section_content = f.read().strip()
        
        # Skip if the section content is empty
        if not section_content:
            logger.info(f"Skipping empty {category} section")
            return category, None
        
        # Generate initial chapter
        chapter_text = self.generate_chapter(section_content, category)
        if not chapter_text:
            logger.error(f"Failed to generate {category} chapter")
            return category, None
            
        # Double check and expand chapter content for methods and results
        if category in ['methods', 'results']:
            logger.info(f"Double checking and expanding {category} chapter")
            chapter_text = self.check_and_expand_chapter(section_content, chapter_text)
            
        # Polish the chapter content
        chapter_text = self.polish_thesis_content(chapter_text)
        
        # Save the chapter
        output_file = os.path.join(working_dir, f"{category.lower().replace(' ', '_')}_chapter.md")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(chapter_text)
            
        logger.info(f"Generated {category} chapter: {output_file}")
        return category, chapter_text
        
    def generate_all_chapters(self, working_dir: str, threads: int = 1) -> Dict[str, str]:
        """Generate all chapters from section files.
        
        Args:
            working_dir: Directory containing section files and where chapter files will be written.
            threads: Number of threads to use for concurrent generation (default: 1 for sequential).
            
        Returns:
            Dictionary mapping categories to generated chapter content.
        """
        generated_chapters = {}
        
        if threads <= 1:
            # Sequential processing (original behavior)
            logger.info("Generating chapters sequentially...")
            for category in self.categories:
                category_result, chapter_text = self._generate_single_chapter_task(category, working_dir)
                if chapter_text:
                    generated_chapters[category_result] = chapter_text
        else:
            # Concurrent processing
            logger.info(f"Generating chapters concurrently using {threads} threads...")
            with ThreadPoolExecutor(max_workers=threads) as executor:
                # Submit all chapter generation tasks
                future_to_category = {
                    executor.submit(self._generate_single_chapter_task, category, working_dir): category
                    for category in self.categories
                }
                
                # Collect results as they complete
                for future in as_completed(future_to_category):
                    category = future_to_category[future]
                    try:
                        category_result, chapter_text = future.result()
                        if chapter_text:
                            generated_chapters[category_result] = chapter_text
                            logger.info(f"Completed {category_result} chapter generation")
                    except Exception as e:
                        logger.error(f"Error generating {category} chapter: {str(e)}")
                        
        logger.info(f"Generated {len(generated_chapters)} chapters total")
        return generated_chapters 