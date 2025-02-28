#!/usr/bin/env python3

# Installation instructions
"""
1. Install required libraries:
   pip install -q -U google-genai
   pip install pillow PyMuPDF tenacity biopython flask
   conda install -c conda-forge pandoc
   conda install tectonic
   brew install pandoc-crossref
2. Set your GOOGLE_API_KEY as an environment variable.
   Get your API key from: https://makersuite.google.com/app/apikey
"""

import os
import argparse
import logging
from gemini_api import GeminiAPI
from text_extractor import TextExtractor
from page_classifier import PageClassifier
from chapter_generator import ChapterGenerator
from yaml_metadata_generator import YamlMetadataGenerator
from thesis_compiler import ThesisCompiler
from citation_generator import CitationGenerator
from figure_generator import FigureGenerator
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_debug_folder(pdf_path: str) -> str:
    """Create and return the debug folder path."""
    pdf_basename = os.path.splitext(os.path.basename(pdf_path))[0]
    debug_folder = os.path.join(os.path.dirname(pdf_path), f"{pdf_basename}_debug")
    os.makedirs(debug_folder, exist_ok=True)
    return debug_folder

def process_pdf(pdf_file, api_key=None, email=None, run_all=True, extract_text=False, 
             categorize_pages=False, generate_chapters=False, add_citations=False, 
             add_figures=False, generate_yaml=False, compile_thesis=False):
    """Process a PDF file and return the path to the debug folder."""
    # Validate PDF file
    if not os.path.exists(pdf_file):
        logger.error(f"PDF file not found: {pdf_file}")
        raise FileNotFoundError(f"PDF file not found: {pdf_file}")

    # Set up paths
    debug_folder = setup_debug_folder(pdf_file)
    extracted_text_file = os.path.join(debug_folder, "extracted_text.txt")
    metadata_file = os.path.join(debug_folder, "thesis_metadata.yaml")
    output_pdf = os.path.join(debug_folder, "thesis.pdf")

    # Use provided API key or get from environment
    api_key = api_key or os.getenv('GEMINI_API_KEY')
    if not api_key:
        logger.error("No API key provided")
        raise ValueError("No API key provided")
    
    # Get email for PubMed API
    email = email or os.getenv('PUBMED_EMAIL')
    if not email:
        logger.error("No email provided for PubMed API")
        raise ValueError("No email provided for PubMed API")
    
    gemini_api = GeminiAPI(api_key=api_key)

    # Run all steps
    if run_all:
        logger.info("Step 1: Extracting text from PDF...")
        extractor = TextExtractor(pdf_file, gemini_api)
        extracted_data = extractor.extract_text(extracted_text_file)
        if not extracted_data:
            logger.error("Text extraction failed")
            raise RuntimeError("Text extraction failed")

        logger.info("Step 2: Categorizing pages...")
        classifier = PageClassifier(gemini_api)
        categorized_content = classifier.classify_pages(extracted_text_file, debug_folder)
        if not categorized_content:
            logger.error("Page categorization failed")
            raise RuntimeError("Page categorization failed")

        logger.info("Step 3: Generating chapters...")
        generator = ChapterGenerator(gemini_api)
        generated_chapters = generator.generate_all_chapters(debug_folder)
        if not generated_chapters:
            logger.error("Chapter generation failed")
            raise RuntimeError("Chapter generation failed")

        logger.info("Step 4: Adding citations to chapters...")
        citation_gen = CitationGenerator(gemini_api, email)
        if not citation_gen.process_chapters(debug_folder):
            logger.error("Citation generation failed")
            raise RuntimeError("Citation generation failed")

        logger.info("Step 5: Adding figure references to chapters...")
        figure_gen = FigureGenerator(gemini_api)
        if not figure_gen.process_chapters(debug_folder):
            logger.error("Figure reference generation failed")
            raise RuntimeError("Figure reference generation failed")

        logger.info("Step 6: Generating YAML metadata...")
        metadata_gen = YamlMetadataGenerator(gemini_api)
        if not metadata_gen.generate_metadata(debug_folder, metadata_file):
            logger.error("YAML metadata generation failed")
            raise RuntimeError("YAML metadata generation failed")

        logger.info("Step 7: Compiling thesis...")
        compiler = ThesisCompiler()
        if not compiler.compile_thesis(debug_folder, metadata_file, output_pdf):
            logger.error("Thesis compilation failed")
            raise RuntimeError("Thesis compilation failed")

        logger.info("All steps completed successfully!")
    else:
        # Run individual steps based on flags
        if extract_text:
            logger.info("Step 1: Extracting text from PDF...")
            extractor = TextExtractor(pdf_file, gemini_api)
            extracted_data = extractor.extract_text(extracted_text_file)
            if not extracted_data:
                logger.error("Text extraction failed")
                raise RuntimeError("Text extraction failed")
            logger.info("Text extraction completed successfully!")
            
        if categorize_pages:
            logger.info("Step 2: Categorizing pages...")
            classifier = PageClassifier(gemini_api)
            categorized_content = classifier.classify_pages(extracted_text_file, debug_folder)
            if not categorized_content:
                logger.error("Page categorization failed")
                raise RuntimeError("Page categorization failed")
            logger.info("Page categorization completed successfully!")
            
        if generate_chapters:
            logger.info("Step 3: Generating chapters...")
            generator = ChapterGenerator(gemini_api)
            generated_chapters = generator.generate_all_chapters(debug_folder)
            if not generated_chapters:
                logger.error("Chapter generation failed")
                raise RuntimeError("Chapter generation failed")
            logger.info("Chapter generation completed successfully!")
            
        if add_citations:
            logger.info("Step 4: Adding citations to chapters...")
            citation_gen = CitationGenerator(gemini_api, email)
            if not citation_gen.process_chapters(debug_folder):
                logger.error("Citation generation failed")
                raise RuntimeError("Citation generation failed")
            logger.info("Citation generation completed successfully!")
            
        if add_figures:
            logger.info("Step 5: Adding figure references to chapters...")
            figure_gen = FigureGenerator(gemini_api)
            if not figure_gen.process_chapters(debug_folder):
                logger.error("Figure reference generation failed")
                raise RuntimeError("Figure reference generation failed")
            logger.info("Figure reference generation completed successfully!")
            
        if generate_yaml:
            logger.info("Step 6: Generating YAML metadata...")
            metadata_gen = YamlMetadataGenerator(gemini_api)
            if not metadata_gen.generate_metadata(debug_folder, metadata_file):
                logger.error("YAML metadata generation failed")
                raise RuntimeError("YAML metadata generation failed")
            logger.info("YAML metadata generation completed successfully!")
            
        if compile_thesis:
            logger.info("Step 7: Compiling thesis...")
            compiler = ThesisCompiler()
            if not compiler.compile_thesis(debug_folder, metadata_file, output_pdf):
                logger.error("Thesis compilation failed")
                raise RuntimeError("Thesis compilation failed")
            logger.info("Thesis compilation completed successfully!")
    
    return debug_folder

def main():
    """Main function to orchestrate the thesis generation process."""
    # Load environment variables
    load_dotenv()
    
    parser = argparse.ArgumentParser(description='Generate a thesis from a PDF presentation.')
    parser.add_argument('pdf_file', help='Path to the input PDF')
    parser.add_argument('--api-key', help='Google Gemini API key (optional if GEMINI_API_KEY is set in .env)')
    parser.add_argument('--email', help='Email for PubMed API (optional if PUBMED_EMAIL is set in .env)')
    parser.add_argument('--extract-text', action='store_true', help='Extract text from PDF')
    parser.add_argument('--categorize-pages', action='store_true', help='Categorize pages')
    parser.add_argument('--generate-chapters', action='store_true', help='Generate chapters')
    parser.add_argument('--add-citations', action='store_true', help='Add citations to chapters')
    parser.add_argument('--add-figures', action='store_true', help='Add figure references to chapters')
    parser.add_argument('--generate-yaml', action='store_true', help='Generate YAML metadata')
    parser.add_argument('--compile', action='store_true', help='Compile thesis PDF')
    args = parser.parse_args()

    # Check if we should run all steps
    run_all = not any([args.extract_text, args.categorize_pages, args.generate_chapters, 
                      args.add_citations, args.add_figures, args.generate_yaml, args.compile])
    
    try:
        process_pdf(
            pdf_file=args.pdf_file, 
            api_key=args.api_key, 
            email=args.email, 
            run_all=run_all,
            extract_text=args.extract_text,
            categorize_pages=args.categorize_pages,
            generate_chapters=args.generate_chapters,
            add_citations=args.add_citations,
            add_figures=args.add_figures,
            generate_yaml=args.generate_yaml,
            compile_thesis=args.compile
        )
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    main() 