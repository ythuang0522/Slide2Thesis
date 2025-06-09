import os
import logging
import subprocess
from typing import List, Optional

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
                      csl_style: Optional[str] = "CSL/acm-sig-proceedings.csl") -> bool:
        """Compile chapters and metadata into a PDF.
        
        Args:
            chapters_dir: Directory containing chapter files.
            metadata_file: Path to YAML metadata file.
            output_pdf: Path for output PDF file.
            csl_style: Path to CSL style file or style name (optional).
                      If None, uses default Chicago author-date style.
                      Popular options: 'CSL/nature.csl', 'CSL/ieee.csl', 'CSL/plos-biology.csl'
            
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
            
            # Construct pandoc command with citeproc and CSL support
            pandoc_cmd = [
                'pandoc',
                '--metadata-file=' + metadata_file,
                '-s',
                '--filter', 'pandoc-crossref',  # Add the pandoc-crossref filter for cross-referencing
                '--citeproc',  # Use pandoc's built-in citation processor
                '--pdf-engine=xelatex',  # Use XeLaTeX for better Unicode support
                f'--resource-path={chapters_dir}',  # Add the chapters directory to the resource path for figure references
                '--bibliography=references.bib',  # Add the bibliography file
                '--metadata=reference-section-title:References',  # Add References heading
            ]
            
            # Add CSL style if specified
            if csl_style:
                if os.path.exists(csl_style):
                    # Full path to CSL file
                    pandoc_cmd.append(f'--csl={csl_style}')
                    logger.info(f"Using CSL style: {csl_style}")
                else:
                    # Try to find CSL file in common locations
                    possible_paths = [
                        csl_style,  # Direct filename
                        f'CSL/{csl_style}',  # In CSL subdirectory
                        f'styles/{csl_style}',  # In styles subdirectory
                        f'CSL/{csl_style}.csl' if not csl_style.endswith('.csl') else f'CSL/{csl_style}',  # Add .csl extension in CSL dir
                        f'{csl_style}.csl' if not csl_style.endswith('.csl') else csl_style,  # Add .csl extension
                    ]
                    
                    csl_found = False
                    for path in possible_paths:
                        if os.path.exists(path):
                            pandoc_cmd.append(f'--csl={path}')
                            logger.info(f"Using CSL style: {path}")
                            csl_found = True
                            break
                    
                    if not csl_found:
                        logger.warning(f"CSL style file '{csl_style}' not found. Using default style.")
            else:
                logger.info("Using default Chicago author-date citation style")
            
            # Add output file and chapter files
            pandoc_cmd.extend(['-o', output_tex] + chapter_files)
            
            # Run pandoc to generate TeX
            logger.info("Running pandoc to generate TeX...")
            subprocess.run(pandoc_cmd, check=True, capture_output=True, text=True)
            
            # Run tectonic to generate PDF - use correct syntax
            logger.info("Running tectonic to generate PDF...")
            subprocess.run(['tectonic', output_tex], 
                          check=True, capture_output=True, text=True)
            
            logger.info(f"Thesis compiled successfully: {output_pdf}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Compilation error: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Error during compilation: {e}")
            return False 