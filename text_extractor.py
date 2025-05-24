import os
import logging
import fitz  # PyMuPDF
from PIL import Image
import io
from typing import List, Dict, Optional
from gemini_api import GeminiAPI

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TextExtractor:
    """Extracts text from a PDF by converting pages to images and using the Gemini API."""
    
    def __init__(self, pdf_path: str, gemini_api: GeminiAPI):
        """Initialize the TextExtractor.
        
        Args:
            pdf_path: Path to the PDF file.
            gemini_api: Instance of GeminiAPI for text extraction.
        """
        self.pdf_path = pdf_path
        self.gemini_api = gemini_api
        
    def pdf_to_images(self, dpi: int = 300) -> List[Image.Image]:
        """Convert PDF pages to PIL Images.
        
        Args:
            dpi: DPI for rendering (default 300 for good OCR quality).
            
        Returns:
            List of PIL Image objects.
        """
        images = []
        pdf_document = None
        
        try:
            pdf_document = fitz.open(self.pdf_path)
            zoom = dpi / 72  # Default PDF DPI is 72
            
            for page_num in range(pdf_document.page_count):
                page = pdf_document[page_num]
                matrix = fitz.Matrix(zoom, zoom).prerotate(page.rotation or 0)
                pix = page.get_pixmap(matrix=matrix, alpha=False)
                img_data = pix.tobytes("jpeg")
                image = Image.open(io.BytesIO(img_data)).convert('RGB')
                images.append(image)
                    
        except Exception as e:
            logger.error(f"Error converting PDF {self.pdf_path} to images: {e}")
            return []
        finally:
            if pdf_document:
                pdf_document.close()
        return images
        
    def extract_text_from_image(self, image: Image.Image, previous_paragraph: Optional[str] = None) -> Optional[str]:
        """Extract text from a single image using Gemini API.
        
        Args:
            image: PIL Image object of the slide.
            previous_paragraph: Text from previous slide for context.
            
        Returns:
            Extracted text or None if extraction fails.
        """
        prompt = """Analyze this slide from a powerpoint presentation of a master thesis. Your goal is to write a detailed description that completely captures the slide's content. 
        
                1. If there are visualizations (figures, charts, graphs, diagrams), explain them like a figure legend and summarize the key messages of the visualizations.

                2. If there are equations in the slide, explain them first and summarize the key messages of the equations. Convert the equations into a markdown format after the paragraph.

                3. If there are tables in the slide, explain them first like a table legend and summarize the key messages of the tables. Convert the tables into a markdown format after the paragraph.
                
                4. Extract the title, aurhor name, and advisor name if clearly visible. Otherwise, don't output anything.
                
                5. Ignore the slide number and other irrelevant information.
                
                6. Write in markdown format.
                
                7. Summarize the key messages of the slide at the end"""
                
        if previous_paragraph:
            prompt += f"""\n\n**Previous slide context:** \n\n{previous_paragraph}\n\nConsidering this context from the previous slide image to write the description provided in the current slide. Ensure the description for this slide logically follows the previous context. However, if the slide is unrelated to previous context (e.g., a new topic or a different section), ignore the previous context and generate a description based solely on the current slide."""
            
        return self.gemini_api.generate_content(prompt, image)
        
    def extract_text(self, output_file: str) -> Dict[str, str]:
        """Extract text from all pages and write to output file.
        
        Args:
            output_file: Path to write the extracted text.
            
        Returns:
            Dictionary mapping page numbers to extracted text.
        """
        images = self.pdf_to_images()
        extracted_data = {}
        previous_paragraph = None
        
        # save the images for debugging, 
        for page_num, image in enumerate(images, 1):
            logger.info(f"Processing page {page_num}/{len(images)}")

            # Save the image for debugging
            image_path = os.path.join(os.path.dirname(output_file), f"page_{page_num}.jpg")
            image.save(image_path, "JPEG", quality=95)

            text = self.extract_text_from_image(image, previous_paragraph)
            
            if text:
                logger.debug("Page %s:\n%s\n\n", page_num, text)
                extracted_data[f"Page {page_num}"] = text
                previous_paragraph = text
            else:
                extracted_data[f"Page {page_num}"] = "Text extraction failed."
                
        # Write extracted text to file
        with open(output_file, 'w', encoding='utf-8') as f:
            for page, text in extracted_data.items():
                f.write(f"*{page}*:\n{text}\n\n")
                
        return extracted_data 