import os
import logging
import subprocess
import shutil
from typing import List
from ..utils.style_manager import StyleManager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ThesisCompiler:
    """Compiles thesis chapters into a PDF using pandoc and tectonic."""
    
    def __init__(self, style: str = 'thesis'):
        """Initialize the ThesisCompiler.
        
        Args:
            style: Style name ('thesis' or 'nature').
        """
        self.style = style
        self.style_config = StyleManager.get_style_config(style)
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
        """Compile chapters and metadata into a PDF using style-specific template.
        
        Args:
            chapters_dir: Directory containing chapter files.
            metadata_file: Path to YAML metadata file.
            output_pdf: Path for output PDF file.
            
        Returns:
            True if compilation succeeds, False otherwise.
        """
        try:
            # Get style-specific template file
            template_file = self.style_config['template_file']
            
            # Check if required files exist
            if not os.path.exists(template_file):
                logger.error(f"Template file not found: {template_file}")
                return False
            
            # Copy style-specific required files
            self._copy_style_files()
                
            # Get chapter files in correct order
            chapter_files = self.get_chapter_files(chapters_dir)
            if not chapter_files:
                logger.error("No chapter files found")
                return False
                
            # Generate intermediate TeX file
            output_tex = os.path.splitext(output_pdf)[0] + '.tex'
            
            # Copy style-specific files to output directory
            output_dir = os.path.dirname(output_tex)
            if output_dir:  # Only if output is in a subdirectory
                os.makedirs(output_dir, exist_ok=True)
                self._copy_style_files_to_output(output_dir)
            
            # Construct pandoc command with style-specific options
            pandoc_cmd = self._build_pandoc_command(chapters_dir, metadata_file, template_file, output_tex)
            
            # Add chapter files to pandoc command
            pandoc_cmd.extend(chapter_files)
            
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
    
    def _copy_style_files(self):
        """Copy required style files to current directory."""
        template_dir = self.style_config['template_dir']
        
        for file_name in self.style_config['required_files']:
            source_path = os.path.join(template_dir, file_name)
                
            if os.path.exists(source_path):
                shutil.copy2(source_path, file_name)
                logger.info(f"Copied {source_path} to {file_name}")
            else:
                logger.warning(f"Required file {file_name} not found at {source_path}")
    
    def _copy_style_files_to_output(self, output_dir: str):
        """Copy style-specific files to output directory."""
        template_dir = self.style_config['template_dir']
        
        for file_name in self.style_config['required_files']:
            source_path = os.path.join(template_dir, file_name)
                
            if os.path.exists(source_path):
                dest_file = os.path.join(output_dir, os.path.basename(file_name))
                shutil.copy2(source_path, dest_file)
                logger.info(f"Copied {source_path} to {dest_file}")
            else:
                logger.warning(f"Required file {file_name} not found at {source_path}")
    
    def _build_pandoc_command(self, chapters_dir: str, metadata_file: str, 
                             template_file: str, output_tex: str) -> List[str]:
        """Build pandoc command with style-specific options."""
        pandoc_cmd = [
            'pandoc',
            '--metadata-file=' + metadata_file,
            '--template=' + template_file,
            '-s',
            '-o', output_tex
        ]
        
        if self.style == 'thesis':
            # Thesis-specific options
            pandoc_cmd.extend([
                '--filter', 'pandoc-crossref',
                '--natbib',
                '--pdf-engine=xelatex',
                f'--resource-path={chapters_dir}',
                '--bibliography=references.bib'
            ])
            logger.info("Using natbib with traditional LaTeX bibliography")
        else:
            # Nature journal options
            pandoc_cmd.extend([
                '--filter', 'pandoc-crossref',
                '--natbib',
                '--pdf-engine=xelatex',
                f'--resource-path={chapters_dir}',
                '--bibliography=references.bib'
            ])
            logger.info("Using Nature journal template with natbib")
            
        return pandoc_cmd 