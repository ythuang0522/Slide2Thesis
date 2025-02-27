import os
import logging
import subprocess
from typing import List

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ThesisCompiler:
    """Compiles thesis chapters into a PDF using pandoc and tectonic."""
    
    def __init__(self):
        """Initialize the ThesisCompiler."""
        self.chapter_order = ['introduction', 'related works', 'methods', 'results', 'conclusions', 'appendix']
        
    def get_chapter_files(self, chapters_dir: str) -> List[str]:
        """Get ordered list of chapter files.
        
        Args:
            chapters_dir: Directory containing chapter files.
            
        Returns:
            List of chapter file paths in correct order.
        """
        chapter_files = []
        for chapter_type in self.chapter_order:
            # First check for chapters with figures
            chapter_file = os.path.join(chapters_dir, f"{chapter_type.lower().replace(' ', '_')}_chapter_with_figures.md")
            
            # If not found, check for cited chapters
            if not os.path.exists(chapter_file):
                chapter_file = os.path.join(chapters_dir, f"{chapter_type.lower().replace(' ', '_')}_chapter_cited.md")
            
            # If still not found, check for regular chapters
            if not os.path.exists(chapter_file):
                chapter_file = os.path.join(chapters_dir, f"{chapter_type.lower().replace(' ', '_')}_chapter.md")
                
            if os.path.exists(chapter_file):
                chapter_files.append(chapter_file)
                
        return chapter_files
        
    def compile_thesis(self, chapters_dir: str, metadata_file: str, output_pdf: str) -> bool:
        """Compile chapters and metadata into a PDF.
        
        Args:
            chapters_dir: Directory containing chapter files.
            metadata_file: Path to YAML metadata file.
            output_pdf: Path for output PDF file.
            
        Returns:
            True if compilation succeeds, False otherwise.
        """
        try:
            # Get chapter files in correct order
            chapter_files = self.get_chapter_files(chapters_dir)
            if not chapter_files:
                logger.error("No chapter files found")
                return False
                
            # Generate intermediate TeX file
            output_tex = os.path.splitext(output_pdf)[0] + '.tex'
            
            # Construct pandoc command
            pandoc_cmd = [
                'pandoc',
                '--metadata-file=' + metadata_file,
                '-s',
                '--natbib',
                f'--resource-path={chapters_dir}',
                '--bibliography=references.bib',
                '--filter', 'pandoc-crossref',
                '-o', output_tex
            ] + chapter_files
            
            # Run pandoc to generate TeX
            logger.info("Running pandoc to generate TeX...")
            subprocess.run(pandoc_cmd, check=True, capture_output=True, text=True)
            
            # Run tectonic to generate PDF
            logger.info("Running tectonic to generate PDF...")
            subprocess.run(['tectonic', output_tex], check=True, capture_output=True, text=True)
            
            logger.info(f"Thesis compiled successfully: {output_pdf}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Compilation error: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Error during compilation: {e}")
            return False 