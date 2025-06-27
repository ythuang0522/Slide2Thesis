"""
Style Manager for handling different document styles (thesis vs journal).
Provides simple configuration management for backwards compatibility.
"""

AVAILABLE_STYLES = {
    'thesis': {
        'document_class': 'Thesis',
        'template_file': 'templates/latex/thesis/thesis-template.tex',
        'template_dir': 'templates/latex/thesis',
        'bibliography_style': 'plain',
        'required_files': ['Thesis.cls', 'lstpatch.sty', 'CCU.pdf'],
        'metadata_type': 'thesis'
    },
    'nature': {
        'document_class': 'sn-jnl',
        'document_options': ['pdflatex', 'sn-nature'],
        'template_file': 'templates/latex/nature/nature-template.tex',
        'template_dir': 'templates/latex/nature',
        'bibliography_style': 'sn-nature',
        'required_files': ['sn-jnl.cls', 'sn-nature.bst'],
        'metadata_type': 'journal'
    }
}

class StyleManager:
    """Simple style configuration manager."""
    
    @staticmethod
    def get_style_config(style_name: str = 'thesis') -> dict:
        """Get configuration for specified style.
        
        Args:
            style_name: Name of the style ('thesis' or 'nature')
            
        Returns:
            Dictionary containing style configuration
        """
        return AVAILABLE_STYLES.get(style_name, AVAILABLE_STYLES['thesis'])
    
    @staticmethod
    def list_styles() -> list:
        """Get list of available styles.
        
        Returns:
            List of available style names
        """
        return list(AVAILABLE_STYLES.keys())
    
    @staticmethod
    def is_valid_style(style_name: str) -> bool:
        """Check if style name is valid.
        
        Args:
            style_name: Name of the style to check
            
        Returns:
            True if style is valid, False otherwise
        """
        return style_name in AVAILABLE_STYLES 