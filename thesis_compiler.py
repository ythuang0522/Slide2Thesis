import os
import logging
import subprocess
import shutil
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
        
    def compile_thesis(self, chapters_dir: str, metadata_file: str, output_pdf: str, 
                      template_file: str = "thesis-template.tex") -> bool:
        """Compile chapters and metadata into a PDF using custom Thesis.cls template.
        
        Args:
            chapters_dir: Directory containing chapter files.
            metadata_file: Path to YAML metadata file.
            output_pdf: Path for output PDF file.
            template_file: Path to custom LaTeX template file.
            
        Returns:
            True if compilation succeeds, False otherwise.
        """
        try:
            # Check if required files exist
            if not os.path.exists(template_file):
                logger.error(f"Template file not found: {template_file}")
                return False
                
            if not os.path.exists("Thesis.cls"):
                logger.error("Thesis.cls not found in current directory")
                logger.info(f"Current working directory: {os.getcwd()}")
                logger.info(f"Files in current directory: {os.listdir('.')}")
                return False
                
            # Get chapter files in correct order
            chapter_files = self.get_chapter_files(chapters_dir)
            if not chapter_files:
                logger.error("No chapter files found")
                return False
                
            # Generate intermediate TeX file
            output_tex = os.path.splitext(output_pdf)[0] + '.tex'
            
            # Copy Thesis.cls and its dependencies to the output directory so tectonic can find them
            output_dir = os.path.dirname(output_tex)
            if output_dir:  # Only if output is in a subdirectory
                os.makedirs(output_dir, exist_ok=True)
                
                # List of LaTeX files and resources to copy
                latex_files_to_copy = ["Thesis.cls", "lstpatch.sty", "CCU.pdf"]
                
                for latex_file in latex_files_to_copy:
                    if os.path.exists(latex_file):
                        dest_file = os.path.join(output_dir, latex_file)
                        shutil.copy2(latex_file, dest_file)
                        logger.info(f"Copied {latex_file} to {dest_file}")
                    else:
                        logger.warning(f"LaTeX dependency {latex_file} not found in project root")
            
            # Construct pandoc command with custom template and natbib
            pandoc_cmd = [
                'pandoc',
                '--metadata-file=' + metadata_file,
                '--template=' + template_file,  # Use custom Thesis.cls template
                '-s',
                '--filter', 'pandoc-crossref',  # Add the pandoc-crossref filter for cross-referencing
                '--natbib',  # Use natbib for traditional LaTeX bibliography
                '--pdf-engine=xelatex',  # Use XeLaTeX for better Unicode support
                f'--resource-path={chapters_dir}',  # Add the chapters directory to the resource path for figure references
                '--bibliography=references.bib',  # Add the bibliography file
            ]
            
            logger.info("Using natbib with traditional LaTeX bibliography")
            
            # Add output file and chapter files
            pandoc_cmd.extend(['-o', output_tex] + chapter_files)
            
            # Run pandoc to generate TeX with Thesis.cls template
            logger.info("Running pandoc to generate TeX with Thesis.cls template...")
            result = subprocess.run(pandoc_cmd, check=True, capture_output=True, text=True)
            logger.info("Pandoc conversion completed successfully")
            
            # Run tectonic to generate PDF with CJK and wallpaper support
            # Run tectonic from the output directory where Thesis.cls was copied
            logger.info("Running tectonic to generate PDF with CJK support...")
            tex_filename = os.path.basename(output_tex)
            tectonic_cwd = output_dir if output_dir else os.getcwd()
            logger.info(f"Tectonic working directory: {tectonic_cwd}")
            logger.info(f"TeX file: {tex_filename}")
            
            result = subprocess.run(['tectonic', tex_filename], 
                          cwd=tectonic_cwd,  # Run from output directory where Thesis.cls is located
                          check=True, capture_output=True, text=True)
            logger.info("Tectonic compilation completed successfully")
            
            logger.info(f"Thesis compiled successfully: {output_pdf}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Compilation error: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Error during compilation: {e}")
            return False 