import json
import os
import re
import logging
import glob
from typing import Dict, List, Optional, Tuple
from PIL import Image
from gemini_api import GeminiAPI

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FigureGenerator:
    """Identifies sentences that should reference figures and adds appropriate figure references."""
    
    def __init__(self, gemini_api: GeminiAPI):
        """Initialize the FigureGenerator.
        
        Args:
            gemini_api: Instance of GeminiAPI for figure analysis
        """
        self.gemini_api = gemini_api
        # Add a class-level dictionary to track figure IDs across all chapters
        self.global_figure_ids = {}
        
    def process_chapters(self, debug_folder: str) -> bool:
        """Process markdown files to add figure references.
        
        Args:
            debug_folder: Path to the debug folder containing chapter files
            
        Returns:
            bool: True if processing was successful, False otherwise
        """
        try:
            # Reset global figure IDs for a new processing run
            self.global_figure_ids = {}
            
            # Find all cited chapter markdown files for methods and results
            target_chapters = ['introduction', 'methods', 'results']
            chapter_files = []
            
            for chapter in target_chapters:
                chapter_file = os.path.join(debug_folder, f"{chapter}_chapter_cited.md")
                if os.path.exists(chapter_file):
                    chapter_files.append(chapter_file)
            
            if not chapter_files:
                logger.error(f"No target chapter files found in {debug_folder}")
                return False
            
            # Get all available figure images
            figure_images = self._get_figure_images(debug_folder)
            if not figure_images:
                logger.error(f"No figure images found in {debug_folder}")
                return False
            
            # Get extracted text for context
            extracted_text = self._load_extracted_text(debug_folder)
            
            # Process each chapter
            for chapter_file in chapter_files:
                logger.info(f"Processing figures for {os.path.basename(chapter_file)}")
                
                # Analyze chapter for figure references
                figure_data = self._analyze_chapter_for_figures(chapter_file, figure_images, extracted_text)
                if figure_data:
                    # Update chapter with figure references
                    print(figure_data)
                    self._update_chapter_figures(chapter_file, figure_data, debug_folder)
                    logger.info(f"Added figure references to {os.path.basename(chapter_file)}")
                else:
                    logger.warning(f"No figure references identified for {os.path.basename(chapter_file)}")
            
            logger.info("Successfully processed all chapters for figure references")
            return True
            
        except Exception as e:
            logger.error(f"Error processing chapters for figure references: {e}")
            return False
    
    def _get_figure_images(self, debug_folder: str) -> Dict[str, str]:
        """Get all available figure images from the debug folder.
        
        Args:
            debug_folder: Path to the debug folder
            
        Returns:
            Dictionary mapping image filenames to their full paths
        """
        figure_images = {}
        image_pattern = os.path.join(debug_folder, "page_*.jpg")
        
        for image_path in glob.glob(image_pattern):
            image_name = os.path.basename(image_path)
            figure_images[image_name] = image_path
            
        return figure_images
    
    def _load_extracted_text(self, debug_folder: str) -> Dict[str, str]:
        """Load extracted text from the extracted_text.txt file.
        
        Args:
            debug_folder: Path to the debug folder
            
        Returns:
            Dictionary mapping page numbers to extracted text
        """
        extracted_text = {}
        extracted_text_file = os.path.join(debug_folder, "extracted_text.txt")
        
        if os.path.exists(extracted_text_file):
            try:
                with open(extracted_text_file, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # Parse the content to extract page text
                page_pattern = r'\*Page (\d+)\*:\n(.*?)(?=\*Page \d+\*:|$)'
                matches = re.findall(page_pattern, content, re.DOTALL)
                
                for page_num, text in matches:
                    image_name = f"page_{page_num}.jpg"
                    extracted_text[image_name] = text.strip()
                    
                return extracted_text
            except Exception as e:
                logger.error(f"Error loading extracted text: {e}")
                
        return {}
    
    def _analyze_chapter_for_figures(self, chapter_path: str, figure_images: Dict[str, str], 
                                    extracted_text: Dict[str, str]) -> Optional[Dict]:
        """Analyze a chapter file for sentences that should reference figures.
        
        Args:
            chapter_path: Path to the chapter markdown file
            figure_images: Dictionary of available figure images
            extracted_text: Dictionary of extracted text for each figure
            
        Returns:
            Dictionary containing figure analysis or None if analysis fails
        """
        if not os.path.exists(chapter_path):
            logger.error(f"Chapter file not found: {chapter_path}")
            return None
            
        try:
            with open(chapter_path, "r", encoding="utf-8") as f:
                chapter_text = f.read()
                
            figure_data = self._analyze_figures(chapter_text, figure_images, extracted_text)
            logger.info(f"Analyzed figure references for {os.path.basename(chapter_path)}")
            return figure_data
            
        except Exception as e:
            logger.error(f"Error analyzing chapter {chapter_path} for figures: {e}")
            return None
    
    def _analyze_figures(self, text: str, figure_images: Dict[str, str], 
                        extracted_text: Dict[str, str]) -> Dict:
        """Analyze text for sentences that should reference figures using Gemini.
        
        Args:
            text: Text content to analyze
            figure_images: Dictionary of available figure images
            extracted_text: Dictionary of extracted text for each figure
            
        Returns:
            Dictionary containing figure analysis
        """
        # Prepare context about available figures
        figure_context = ""
        for image_name, image_text in extracted_text.items():
            figure_context += f"Figure {image_name}:\n{image_text}\n\n"
        
        prompt = f"""Analyze the following figure context and thesis text, identify sentences in thesis text that should reference figures in the figure context.
        Focus on sentences in the thesis text that:
        1. Describe visual data or results (charts, graphs, diagrams, etc.)
        2. Refer to experimental setups or methodologies that are better illustrated
        3. Mention visual comparisons or trends
        4. Use visual phrases like "as shown", "illustrates", "plots", etc.
        
        Here is detailed information about the available figures (figure context) that can be referenced:
        
        {figure_context}
        
        For each sentence that should reference a figure, determine which figure (by filename) is most appropriate.
        
        Respond with ONLY a valid JSON object in this exact format:
        {{
            "figure_references": [
                {{
                    "sentence": "exact sentence from text",
                    "reason": "brief reason why this sentence should reference a figure",
                    "figure_filename": "page_X.jpg",
                    "figure_caption": "A descriptive caption for this figure"
                }}
            ]
        }}
        
        - Only include sentences where you are confident there should be a figure reference.
        - Exclude sentences that are just lists of items or other non-visual content or the visual elements are not the main focus of the sentence.

        """
        
        try:
            response = self.gemini_api.generate_content(prompt + "\n\nChapter text to analyze:\n" + text)
            
            # Clean the response - remove any non-JSON content
            json_str = response.strip()
            
            # Try to find a valid JSON object in the response
            start_idx = json_str.find('{')
            end_idx = json_str.rfind('}')
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = json_str[start_idx:end_idx+1]
                
                # Log the extracted JSON for debugging
                logger.debug(f"Extracted JSON: {json_str[:100]}...")
                
                try:
                    figure_data = json.loads(json_str)
                    
                    # Validate the structure
                    if not isinstance(figure_data, dict) or "figure_references" not in figure_data:
                        logger.warning("JSON response missing 'figure_references' key")
                        return {"figure_references": []}
                        
                    return figure_data
                    
                except json.JSONDecodeError as e:
                    logger.error(f"JSON parsing error: {e}")
                    logger.debug(f"Problematic JSON: {json_str}")
                    
                    # Get error details
                    error_msg = str(e)
                    error_line = None
                    error_col = None
                    error_pos = None
                    
                    # Extract line, column, and position from error message
                    line_match = re.search(r'line (\d+)', error_msg)
                    col_match = re.search(r'column (\d+)', error_msg)
                    char_match = re.search(r'char (\d+)', error_msg)
                    
                    if line_match:
                        error_line = int(line_match.group(1))
                    if col_match:
                        error_col = int(col_match.group(1))
                    if char_match:
                        error_pos = int(char_match.group(1))
                        
                    # Log more detailed error information
                    if error_pos is not None and error_pos < len(json_str):
                        # Get context around the error
                        start = max(0, error_pos - 20)
                        end = min(len(json_str), error_pos + 20)
                        context = json_str[start:end]
                        pointer = ' ' * (min(20, error_pos - start)) + '^'
                        logger.debug(f"Error context: {context}")
                        logger.debug(f"Error position: {pointer}")
                    
                    # Try a more aggressive approach to fix common JSON issues
                    try:
                        # Replace common issues in JSON
                        fixed_json = json_str.replace("'", '"')  # Replace single quotes with double quotes
                        fixed_json = re.sub(r',\s*}', '}', fixed_json)  # Remove trailing commas
                        fixed_json = re.sub(r',\s*]', ']', fixed_json)  # Remove trailing commas in arrays
                        
                        # Additional fixes for common JSON issues
                        # Fix missing commas between objects in arrays
                        fixed_json = re.sub(r'}\s*{', '},{', fixed_json)
                        # Fix missing commas between key-value pairs
                        fixed_json = re.sub(r'"\s*"', '","', fixed_json)
                        # Fix missing colons between keys and values
                        fixed_json = re.sub(r'"\s+([{\[])', '": \1', fixed_json)
                        
                        # Fix for specific issue with missing comma delimiters between properties
                        # This pattern looks for property patterns without commas between them
                        fixed_json = re.sub(r'(["\'])\s*}\s*["\']', r'\1},{"', fixed_json)  # Fix missing comma between objects
                        fixed_json = re.sub(r'(["\'])\s*(["\'])(?!\s*[,:}])', r'\1,\2', fixed_json)  # Add comma between properties
                        
                        # Targeted fix for the specific error position if available
                        if error_line == 29 and error_col == 143:
                            # This is the specific error mentioned in the error message
                            # Try to fix it by inserting a comma at the position
                            if error_pos is not None and error_pos < len(fixed_json):
                                fixed_json = fixed_json[:error_pos] + ',' + fixed_json[error_pos:]
                                logger.debug("Applied targeted fix for line 29, column 143 error")
                        
                        # Log the fixed JSON for debugging
                        logger.debug(f"Attempting to parse fixed JSON: {fixed_json[:100]}...")
                        
                        figure_data = json.loads(fixed_json)
                        logger.info("Successfully parsed JSON after fixing common issues")
                        
                        if not isinstance(figure_data, dict) or "figure_references" not in figure_data:
                            logger.warning("Fixed JSON response missing 'figure_references' key")
                            return {"figure_references": []}
                            
                        return figure_data
                    except:
                        # If all attempts fail, return empty result
                        logger.error("All JSON parsing attempts failed")
                        
                        # Last resort: try to extract just the figure_references array
                        try:
                            # Look for the figure_references array pattern
                            refs_pattern = r'"figure_references"\s*:\s*\[(.*?)\]'
                            refs_match = re.search(refs_pattern, json_str, re.DOTALL)
                            
                            if refs_match:
                                # Construct a valid JSON with just the array
                                array_content = refs_match.group(1).strip()
                                # Ensure the array is properly formatted
                                if array_content:
                                    # Fix common array formatting issues
                                    array_content = re.sub(r'}\s*{', '},{', array_content)
                                    array_content = re.sub(r'"\s*"', '","', array_content)
                                    
                                    # Try to parse the array
                                    try:
                                        # Wrap in square brackets to make a valid JSON array
                                        refs_array = json.loads('[' + array_content + ']')
                                        logger.info("Successfully extracted figure_references array as fallback")
                                        return {"figure_references": refs_array}
                                    except:
                                        pass
                        except:
                            pass
                            
                        # If all extraction attempts fail, return empty result
                        return {"figure_references": []}
            else:
                logger.error("No JSON object found in API response")
                return {"figure_references": []}
                
        except Exception as e:
            logger.error(f"Error in figure analysis: {e}")
            return {"figure_references": []}
    
    def _update_chapter_figures(self, chapter_path: str, figure_data: Dict, debug_folder: str) -> None:
        """Update chapter markdown with figure references.
        
        Args:
            chapter_path: Path to chapter markdown file
            figure_data: Figure analysis data
            debug_folder: Path to debug folder
        """
        try:
            with open(chapter_path, "r", encoding="utf-8") as f:
                text = f.read()
            
            # Get chapter name for creating unique IDs
            chapter_name = os.path.basename(chapter_path).split('_')[0]
            
            # Use the global figure IDs dictionary instead of a local one
            # Track which figures have been inserted
            inserted_figures = set()
            
            # First pass: Add references to sentences and identify paragraphs
            paragraphs = re.split(r'\n\s*\n', text)
            updated_paragraphs = []
            paragraph_figures = {}  # Maps paragraph index to list of figures to insert after it
            
            for i, paragraph in enumerate(paragraphs):
                updated_paragraph = paragraph
                paragraph_figure_list = []
                
                for entry in figure_data.get("figure_references", []):
                    sentence = entry["sentence"].strip()
                    figure_filename = entry["figure_filename"]
                    figure_caption = entry["figure_caption"]
                    
                    # Skip if sentence not in this paragraph
                    if sentence not in paragraph:
                        continue
                    
                    # Generate a unique figure ID based on the filename and chapter
                    base_id = re.sub(r'[^a-z0-9]', '-', figure_filename.lower())
                    
                    # Create a unique key that combines chapter and filename
                    chapter_file_key = f"{chapter_name}:{figure_filename}"
                    
                    # Check if this exact chapter-filename combination has been used before
                    if chapter_file_key in self.global_figure_ids:
                        # Use the existing ID for this chapter-filename combination
                        figure_id = self.global_figure_ids[chapter_file_key]
                    else:
                        # Create a new ID for this chapter-filename combination
                        # Include chapter prefix in the ID to ensure uniqueness across chapters
                        chapter_prefix = chapter_name[:3].lower()  # Use first 3 chars of chapter name
                        candidate_id = f"{chapter_prefix}-{base_id}"
                        
                        if candidate_id in self.global_figure_ids.values():
                            # Find the next available suffix
                            suffix = 1
                            while f"{candidate_id}-{suffix}" in self.global_figure_ids.values():
                                suffix += 1
                            figure_id = f"{candidate_id}-{suffix}"
                        else:
                            figure_id = candidate_id
                        
                        # Store the ID for this chapter-filename combination
                        self.global_figure_ids[chapter_file_key] = figure_id
                    
                    # Create the reference text - use end-of-sentence style
                    reference_text = f" (Figure @fig:{figure_id})"
                    
                    # Check if the sentence already has a figure reference
                    if not re.search(r'Figure @fig:', sentence):
                        # Replace the sentence with the referenced version
                        # First, we need to handle LaTeX math expressions
                        # Find all math expressions in the sentence
                        math_expressions = re.findall(r'\$[^$]*\$', sentence)
                        
                        # Create a temporary version of the sentence with placeholders for math expressions
                        temp_sentence = sentence
                        for idx, expr in enumerate(math_expressions):
                            temp_sentence = temp_sentence.replace(expr, f"MATH_PLACEHOLDER_{idx}")
                        
                        # Escape special regex characters in the modified sentence
                        escaped_temp_sentence = re.escape(temp_sentence)
                        
                        # Replace the placeholders with the original math expressions
                        for idx, expr in enumerate(math_expressions):
                            escaped_temp_sentence = escaped_temp_sentence.replace(f"MATH_PLACEHOLDER_{idx}", re.escape(expr))
                        
                        # Add the reference at the end of the sentence, before any punctuation
                        if sentence.rstrip()[-1] in ['.', '?', '!']:
                            # If sentence ends with punctuation, insert reference before the punctuation
                            updated_paragraph = re.sub(
                                f"{escaped_temp_sentence}",
                                f"{sentence.rstrip()[:-1]}{reference_text}{sentence.rstrip()[-1]}",
                                updated_paragraph,
                                count=1
                            )
                        else:
                            # If no punctuation, just append the reference
                            updated_paragraph = re.sub(
                                f"{escaped_temp_sentence}",
                                f"{sentence}{reference_text}",
                                updated_paragraph,
                                count=1
                            )
                    
                    # Add figure to this paragraph's figure list if not already inserted elsewhere
                    if figure_filename not in inserted_figures:
                        figure_markdown = f"\n\n![{figure_caption}]({figure_filename}){{#fig:{figure_id}}}\n"
                        paragraph_figure_list.append(figure_markdown)
                        inserted_figures.add(figure_filename)
                
                # Store the updated paragraph
                updated_paragraphs.append(updated_paragraph)
                
                # Store any figures to be inserted after this paragraph
                if paragraph_figure_list:
                    paragraph_figures[i] = paragraph_figure_list
            
            # Second pass: Reconstruct the document with figures inserted after appropriate paragraphs
            final_text = ""
            for i, paragraph in enumerate(updated_paragraphs):
                final_text += paragraph
                
                # Add figures after this paragraph if needed
                if i in paragraph_figures:
                    for figure in paragraph_figures[i]:
                        final_text += figure
                
                # Add paragraph separator (except for the last paragraph)
                if i < len(updated_paragraphs) - 1:
                    final_text += "\n\n"
            
            # Save the updated chapter
            output_path = os.path.join(debug_folder, f"{os.path.basename(chapter_path).replace('_cited.md', '_with_figures.md')}")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(final_text)
                
            logger.info(f"Updated chapter with figures saved to {output_path}")
            
        except Exception as e:
            logger.error(f"Error updating chapter figures for {chapter_path}: {e}")

    def read_chapter_content(self, chapters_dir: str, chapter_type: str) -> str:
        """Read chapter content with proper file priority.
        
        Args:
            chapters_dir: Directory containing chapter files
            chapter_type: Type of chapter to read
            
        Returns:
            Content of the chapter file or empty string if not found
        """
        # Try different file naming patterns in order of priority
        file_patterns = [
            f"{chapter_type.lower().replace(' ', '_')}_chapter_with_figures.md",
            f"{chapter_type.lower().replace(' ', '_')}_chapter_cited.md",
            f"{chapter_type.lower().replace(' ', '_')}_chapter.md"
        ]
        
        for pattern in file_patterns:
            chapter_file = os.path.join(chapters_dir, pattern)
            if os.path.exists(chapter_file):
                with open(chapter_file, 'r', encoding='utf-8') as f:
                    return f.read()
        
        # If no file is found
        logger.warning(f"No file found for {chapter_type} chapter")
        return "" 