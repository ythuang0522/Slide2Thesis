#!/usr/bin/env python3

import os
import argparse
import logging
from src.ai.api_factory import create_ai_api
from src.processors.text_extractor import TextExtractor
from src.processors.page_classifier import PageClassifier
from src.processors.chapter_generator import ChapterGenerator
from src.processors.yaml_metadata_generator import YamlMetadataGenerator
from src.processors.thesis_compiler import ThesisCompiler
from src.processors.citation_generator import CitationGenerator
from src.processors.figure_generator import FigureGenerator
from src.utils.style_manager import StyleManager
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

def setup_debug_folder(pdf_path: str) -> str:
    """Create and return the debug folder path."""
    pdf_basename = os.path.splitext(os.path.basename(pdf_path))[0]
    debug_folder = os.path.join(os.path.dirname(pdf_path), f"{pdf_basename}_debug")
    os.makedirs(debug_folder, exist_ok=True)
    return debug_folder

def process_pdf(pdf_file, provider=None, model=None, gemini_api_key=None, openai_api_key=None, 
               email=None, google_api_key=None, google_engine_id=None, threads=1, style='thesis', crop_top_pixels=240, run_all=True, extract_text=False, 
               categorize_pages=False, generate_chapters=False, add_citations=False, 
               add_figures=False, generate_yaml=False, compile_thesis=False):
    """Process a PDF file and return the path to the debug folder."""
    # Validate PDF file
    if not os.path.exists(pdf_file):
        logger.error(f"PDF file not found: {pdf_file}")
        raise FileNotFoundError(f"PDF file not found: {pdf_file}")
    if not pdf_file.lower().endswith('.pdf'):
        logger.error(f"Input file is not a PDF: {pdf_file}")
        raise ValueError(f"Input file is not a PDF: {pdf_file}")

    # Set up paths
    debug_folder = setup_debug_folder(pdf_file)
    extracted_text_file = os.path.join(debug_folder, "extracted_text.txt")
    metadata_file = os.path.join(debug_folder, "thesis_metadata.yaml")
    output_pdf = os.path.join(debug_folder, "thesis.pdf")

    # Get email for PubMed API
    email = email or os.getenv('PUBMED_EMAIL')
    if not email:
        logger.error("No email provided for PubMed API")
        raise ValueError("No email provided for PubMed API")
    
    # Check for Google API credentials (optional, for enhanced search)
    google_api_key = google_api_key or os.getenv('GOOGLE_API_KEY')
    google_engine_id = google_engine_id or os.getenv('GOOGLE_ENGINE_ID')
    if not google_api_key or not google_engine_id:
        logger.warning("Google API credentials not found. Google search will be disabled.")
        logger.info("To enable Google search, set GOOGLE_API_KEY and GOOGLE_ENGINE_ID environment variables.")
    
    # Create AI API instance using factory
    ai_api = create_ai_api(
        provider=provider,
        model=model,
        gemini_api_key=gemini_api_key,
        openai_api_key=openai_api_key
    )
    
    logger.info(f"Using {ai_api.provider_name} provider with model: {ai_api.model_name}")

    # Run all steps
    if run_all:
        logger.info("Step 1: Extracting text from PDF...")
        extractor = TextExtractor(pdf_file, ai_api)
        extracted_data = extractor.extract_text(extracted_text_file)
        if not extracted_data:
            logger.error("Text extraction failed")
            raise RuntimeError("Text extraction failed")

        logger.info("Step 2: Categorizing pages...")
        classifier = PageClassifier(ai_api)
        categorized_content = classifier.classify_pages(extracted_text_file, debug_folder)
        if not categorized_content:
            logger.error("Page categorization failed")
            raise RuntimeError("Page categorization failed")

        logger.info("Step 3: Generating chapters...")
        generator = ChapterGenerator(ai_api)
        generated_chapters = generator.generate_all_chapters(debug_folder, threads=threads)
        if not generated_chapters:
            logger.error("Chapter generation failed")
            raise RuntimeError("Chapter generation failed")

        logger.info("Step 4: Adding citations to chapters...")
        citation_gen = CitationGenerator(ai_api, email, google_api_key, google_engine_id)
        if not citation_gen.process_chapters(debug_folder, threads=threads):
            logger.error("Citation generation failed")
            raise RuntimeError("Citation generation failed")

        logger.info("Step 5: Adding figure references to chapters...")
        figure_gen = FigureGenerator(ai_api, crop_top_pixels=crop_top_pixels)
        if not figure_gen.process_chapters(debug_folder, threads=threads):
            logger.error("Figure reference generation failed")
            raise RuntimeError("Figure reference generation failed")

        logger.info("Step 6: Generating YAML metadata...")
        metadata_gen = YamlMetadataGenerator(ai_api, style=style)
        if not metadata_gen.generate_metadata(debug_folder, metadata_file):
            logger.error("YAML metadata generation failed")
            raise RuntimeError("YAML metadata generation failed")

        logger.info("Step 7: Compiling thesis...")
        compiler = ThesisCompiler(style=style)
        if not compiler.compile_thesis(debug_folder, metadata_file, output_pdf):
            logger.error("Thesis compilation failed")
            raise RuntimeError("Thesis compilation failed")

        logger.info("All steps completed successfully!")
    else:
        # Run individual steps based on flags
        if extract_text:
            logger.info("Step 1: Extracting text from PDF...")
            extractor = TextExtractor(pdf_file, ai_api)
            extracted_data = extractor.extract_text(extracted_text_file)
            if not extracted_data:
                logger.error("Text extraction failed")
                raise RuntimeError("Text extraction failed")
            logger.info("Text extraction completed successfully!")
            
        if categorize_pages:
            logger.info("Step 2: Categorizing pages...")
            classifier = PageClassifier(ai_api)
            categorized_content = classifier.classify_pages(extracted_text_file, debug_folder)
            if not categorized_content:
                logger.error("Page categorization failed")
                raise RuntimeError("Page categorization failed")
            logger.info("Page categorization completed successfully!")
            
        if generate_chapters:
            logger.info("Step 3: Generating chapters...")
            generator = ChapterGenerator(ai_api)
            generated_chapters = generator.generate_all_chapters(debug_folder, threads=threads)
            if not generated_chapters:
                logger.error("Chapter generation failed")
                raise RuntimeError("Chapter generation failed")
            logger.info("Chapter generation completed successfully!")
            
        if add_citations:
            logger.info("Step 4: Adding citations to chapters...")
            citation_gen = CitationGenerator(ai_api, email, google_api_key, google_engine_id)
            if not citation_gen.process_chapters(debug_folder, threads=threads):
                logger.error("Citation generation failed")
                raise RuntimeError("Citation generation failed")
            logger.info("Citation generation completed successfully!")
            
        if add_figures:
            logger.info("Step 5: Adding figure references to chapters...")
            figure_gen = FigureGenerator(ai_api, crop_top_pixels=crop_top_pixels)
            if not figure_gen.process_chapters(debug_folder, threads=threads):
                logger.error("Figure reference generation failed")
                raise RuntimeError("Figure reference generation failed")
            logger.info("Figure reference generation completed successfully!")
            
        if generate_yaml:
            logger.info("Step 6: Generating YAML metadata...")
            metadata_gen = YamlMetadataGenerator(ai_api, style=style)
            if not metadata_gen.generate_metadata(debug_folder, metadata_file):
                logger.error("YAML metadata generation failed")
                raise RuntimeError("YAML metadata generation failed")
            logger.info("YAML metadata generation completed successfully!")
            
        if compile_thesis:
            logger.info("Step 7: Compiling thesis...")
            compiler = ThesisCompiler(style=style)
            if not compiler.compile_thesis(debug_folder, metadata_file, output_pdf):
                logger.error("Thesis compilation failed")
                raise RuntimeError("Thesis compilation failed")
            logger.info("Thesis compilation completed successfully!")
    
    return debug_folder

def main():
    """Main function to orchestrate the thesis generation process."""
    # Load environment variables
    load_dotenv(override=True)
    
    parser = argparse.ArgumentParser(description='Generate a thesis from a PDF presentation.')
    parser.add_argument('pdf_file', nargs='?', help='Path to the input PDF')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable debug logging')
    
    # API Provider and Model arguments
    parser.add_argument('--provider', choices=['gemini', 'openai', 'auto'], default='auto',
                       help='AI API provider to use (default: auto-detect from model)')
    parser.add_argument('-m', '--model', help='Model name to use (auto-detects provider if not specified)')
    
    # API Key arguments
    parser.add_argument('--gemini-api-key', help='Gemini API key (optional if GEMINI_API_KEY is set in .env)')
    parser.add_argument('--openai-api-key', help='OpenAI API key (optional if OPENAI_API_KEY is set in .env)')
    
    # Style arguments
    parser.add_argument('--style', choices=StyleManager.list_styles(), default='thesis',
                       help='Output style: thesis (default) or nature journal')
    parser.add_argument('--list-styles', action='store_true',
                       help='List available output styles')
    
    # Other arguments
    parser.add_argument('-e', '--email', help='Email for PubMed API (optional if PUBMED_EMAIL is set in .env)')
    parser.add_argument('--google-api-key', help='Google Custom Search API key (optional if GOOGLE_API_KEY is set in .env)')
    parser.add_argument('--google-engine-id', help='Google Custom Search Engine ID (optional if GOOGLE_ENGINE_ID is set in .env)')
    parser.add_argument('-t', '--threads', type=int, default=6, help='Number of threads for concurrent processing (default: 6)')
    parser.add_argument('--crop-top-pixels', type=int, default=245, help='Number of pixels to crop from top of images (default: 240, no cropping)')

        
    # Step selection arguments
    parser.add_argument('--extract-text', action='store_true', help='Extract text from PDF')
    parser.add_argument('--categorize-pages', action='store_true', help='Categorize pages')
    parser.add_argument('--generate-chapters', action='store_true', help='Generate chapters')
    parser.add_argument('--add-citations', action='store_true', help='Add citations to chapters')
    parser.add_argument('--add-figures', action='store_true', help='Add figure references to chapters')
    parser.add_argument('--generate-yaml', action='store_true', help='Generate YAML metadata')
    parser.add_argument('--compile', action='store_true', help='Compile thesis PDF')
    
    args = parser.parse_args()
    
    # Handle list-styles option
    if args.list_styles:
        print("Available output styles:")
        for style in StyleManager.list_styles():
            style_config = StyleManager.get_style_config(style)
            print(f"  {style}: {style_config['metadata_type']} format")
        return 0

    # Set up logging level based on verbose flag
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        force=True  # Override any existing configuration
    )
    
    if args.verbose:
        logger.info("Debug logging enabled")
    
    # Check if pdf_file is required but not provided
    if not args.pdf_file and not args.list_styles:
        parser.error("pdf_file is required unless using --list-styles")

    model = args.model

    # Check if we should run all steps
    run_all = not any([args.extract_text, args.categorize_pages, args.generate_chapters, 
                      args.add_citations, args.add_figures, args.generate_yaml, args.compile])
    
    try:
        process_pdf(
            pdf_file=args.pdf_file, 
            provider=args.provider,
            model=model,
            gemini_api_key=args.gemini_api_key,
            openai_api_key=args.openai_api_key,
            email=args.email,
            google_api_key=args.google_api_key,
            google_engine_id=args.google_engine_id,
            threads=args.threads,
            style=args.style,
            crop_top_pixels=args.crop_top_pixels,
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