import re
from typing import List, Tuple, Dict
import logging

logger = logging.getLogger(__name__)

class MathFormatter:
    """Formats mathematical content in text by detecting patterns and adding LaTeX delimiters."""
    
    def __init__(self):
        # Mathematical symbols that should be in math mode
        self.math_symbols = {
            '±', '×', '÷', '≤', '≥', '≠', '≈', '∞', '∑', '∏', '∫',
            'α', 'β', 'γ', 'δ', 'ε', 'θ', 'λ', 'μ', 'π', 'σ', 'φ', 'ω',
            'Α', 'Β', 'Γ', 'Δ', 'Θ', 'Λ', 'Π', 'Σ', 'Φ', 'Ω'
        }
        
        # Unicode to LaTeX symbol mapping
        self.unicode_to_latex = {
            '≤': r'\leq',
            '≥': r'\geq',
            '≠': r'\neq',
            '≈': r'\approx',
            '±': r'\pm',
            '×': r'\times',
            '÷': r'\div',
            '∞': r'\infty',
            '∑': r'\sum',
            '∏': r'\prod',
            '∫': r'\int',
            'α': r'\alpha',
            'β': r'\beta',
            'γ': r'\gamma',
            'δ': r'\delta',
            'ε': r'\epsilon',
            'θ': r'\theta',
            'λ': r'\lambda',
            'μ': r'\mu',
            'π': r'\pi',
            'σ': r'\sigma',
            'φ': r'\phi',
            'ω': r'\omega',
        }
        
        # Patterns for different math constructs
        self.patterns = {
            # Simple equations: a = b + c, x = 5, etc.
            'equations': r'\b([a-zA-Z]+\s*[=<>≤≥≠]\s*[a-zA-Z0-9\s+\-*/^()]+)',
            
            # Fractions: 1/2, a/b, (x+1)/(y-2)
            'fractions': r'(\([^)]+\)/\([^)]+\)|[a-zA-Z0-9]+/[a-zA-Z0-9]+)',
            
            # Subscripts: H_2O, x_1, a_i
            'subscripts': r'([a-zA-Z]+)_([a-zA-Z0-9]+)',
            
            # Superscripts: x^2, e^(x+1), 10^3
            'superscripts': r'([a-zA-Z0-9]+)\^(\([^)]+\)|[a-zA-Z0-9]+)',
            
            # Variables: single letters in scientific context
            'variables': r'\b([a-zA-Z])\b(?!\w)',
        }
    
    def format_content(self, content: str) -> str:
        """Main function to format mathematical content in text.
        
        Args:
            content: Input text content to format.
            
        Returns:
            Text with mathematical expressions properly formatted for LaTeX.
        """
        logger.debug("Starting math formatting")
        
        # Step 1: Protect already formatted math
        protected_content, math_blocks = self._protect_existing_math(content)
        
        # Step 2: Detect and format math patterns
        formatted_content = self._detect_and_format_math(protected_content)
        
        # Step 3: Restore protected math blocks
        final_content = self._restore_protected_math(formatted_content, math_blocks)
        
        logger.debug("Math formatting completed")
        return final_content
    
    def _protect_existing_math(self, content: str) -> Tuple[str, Dict[str, str]]:
        """Protect already formatted math from being processed again."""
        math_blocks = {}
        counter = 0
        
        # Protect display math \[...\]
        def replace_display_math(match):
            nonlocal counter
            placeholder = f"__MATH_DISPLAY_{counter}__"
            math_blocks[placeholder] = match.group(0)
            counter += 1
            return placeholder
        
        # Protect inline math $...$
        def replace_inline_math(match):
            nonlocal counter
            placeholder = f"__MATH_INLINE_{counter}__"
            math_blocks[placeholder] = match.group(0)
            counter += 1
            return placeholder
        
        # Protect inline math \(...\)
        def replace_paren_math(match):
            nonlocal counter
            placeholder = f"__MATH_PAREN_{counter}__"
            math_blocks[placeholder] = match.group(0)
            counter += 1
            return placeholder
        
        content = re.sub(r'\\\[.*?\\\]', replace_display_math, content, flags=re.DOTALL)
        content = re.sub(r'\$[^$]+\$', replace_inline_math, content)
        content = re.sub(r'\\\(.*?\\\)', replace_paren_math, content, flags=re.DOTALL)
        
        return content, math_blocks
    
    def _detect_and_format_math(self, content: str) -> str:
        """Detect mathematical patterns and wrap them in math delimiters."""
        lines = content.split('\n')
        formatted_lines = []
        
        for line in lines:
            formatted_line = self._format_line(line)
            formatted_lines.append(formatted_line)
        
        return '\n'.join(formatted_lines)
    
    def _format_line(self, line: str) -> str:
        """Format mathematical content in a single line."""
        # Skip if line is already heavily formatted or is a LaTeX command
        if line.strip().startswith('\\') or line.count('$') >= 2:
            return line
        
        # Skip markdown headers and other structural elements
        if line.strip().startswith('#') or line.strip().startswith('*') or line.strip().startswith('-'):
            return line
        
        # Skip lines containing math placeholders
        if '__MATH_' in line:
            return line
        
        original_line = line
        
        # Check for mathematical symbols first
        if any(symbol in line for symbol in self.math_symbols):
            line = self._wrap_symbols_in_math(line)
        
        # Check for equations (highest priority)
        equation_matches = list(re.finditer(self.patterns['equations'], line))
        for match in reversed(equation_matches):  # Process from right to left to maintain positions
            line = self._format_equation(line, match)
        
        # Check for fractions
        fraction_matches = list(re.finditer(self.patterns['fractions'], line))
        for match in reversed(fraction_matches):
            line = self._format_fraction(line, match)
        
        # Check for subscripts and superscripts
        line = self._format_scripts(line)
        
        # Check for isolated variables in scientific context
        line = self._format_variables(line)
        
        # Clean up any double math formatting
        line = self._clean_double_math(line)
        
        return line
    
    def _format_equation(self, line: str, match: re.Match) -> str:
        """Format equations with proper math delimiters."""
        equation = match.group(1)
        
        # Skip if already in math mode
        start_pos = match.start()
        if start_pos > 0 and line[start_pos-1] == '$':
            return line
        
        # Determine if this should be display or inline math
        if self._should_be_display_math(line, equation):
            formatted_eq = f"\\[{equation}\\]"
        else:
            formatted_eq = f"${equation}$"
        
        return line[:match.start()] + formatted_eq + line[match.end():]
    
    def _format_fraction(self, line: str, match: re.Match) -> str:
        """Convert fractions to LaTeX format."""
        fraction = match.group(1)
        
        # Skip if already in math mode
        start_pos = match.start()
        if start_pos > 0 and line[start_pos-1] == '$':
            return line
        
        # Parse numerator and denominator
        if '(' in fraction:
            # Complex fraction: (x+1)/(y-2)
            parts = fraction.split('/')
            numerator = parts[0].strip('()')
            denominator = parts[1].strip('()')
        else:
            # Simple fraction: a/b
            parts = fraction.split('/')
            numerator = parts[0]
            denominator = parts[1]
        
        latex_fraction = f"$\\frac{{{numerator}}}{{{denominator}}}$"
        return line[:match.start()] + latex_fraction + line[match.end():]
    
    def _format_scripts(self, line: str) -> str:
        """Format subscripts and superscripts."""
        # Subscripts
        def replace_subscript(match):
            if match.start() > 0 and line[match.start()-1] == '$':
                return match.group(0)  # Already in math mode
            return f"${match.group(1)}_{{{match.group(2)}}}$"
        
        line = re.sub(self.patterns['subscripts'], replace_subscript, line)
        
        # Superscripts
        def replace_superscript(match):
            base = match.group(1)
            exp = match.group(2)
            # Check if already in math mode
            start_pos = match.start()
            if start_pos > 0 and line[start_pos-1] == '$':
                return match.group(0)
            return f"${base}^{{{exp}}}$"
        
        line = re.sub(self.patterns['superscripts'], replace_superscript, line)
        
        return line
    
    def _format_variables(self, line: str) -> str:
        """Format isolated variables in scientific context."""
        # Only format variables if they appear in scientific context
        scientific_context_words = [
            'variable', 'parameter', 'coefficient', 'constant', 'value',
            'equation', 'formula', 'expression', 'function', 'where',
            'let', 'given', 'assume', 'denote', 'represent', 'calculate',
            'measured', 'obtained', 'determined', 'estimated'
        ]
        
        if any(word in line.lower() for word in scientific_context_words):
            # Format single letters that are likely variables
            def replace_variable(match):
                var = match.group(1)
                start_pos = match.start()
                # Don't format if already in math mode or if it's a common word
                if start_pos > 0 and line[start_pos-1] == '$':
                    return var
                # Skip common single letters that are usually not variables
                if var.lower() in ['a', 'i', 'o', 'A', 'I', 'O']:
                    return var
                return f"${var}$"
            
            line = re.sub(r'\b([a-zA-Z])\b(?=\s|[,.])', replace_variable, line)
        
        return line
    
    def _wrap_symbols_in_math(self, line: str) -> str:
        """Wrap mathematical symbols in math delimiters and convert Unicode to LaTeX."""
        for symbol in self.math_symbols:
            if symbol in line:
                # Get LaTeX equivalent if available
                latex_symbol = self.unicode_to_latex.get(symbol, symbol)
                
                # Only wrap if not already in math mode
                pattern = re.escape(symbol)
                def replace_symbol(match):
                    start_pos = match.start()
                    if start_pos > 0 and line[start_pos-1] == '$':
                        return symbol
                    return f'${latex_symbol}$'
                
                line = re.sub(pattern, replace_symbol, line)
        return line
    
    def _should_be_display_math(self, line: str, equation: str) -> bool:
        """Determine if equation should be display math or inline."""
        # Display math if:
        # 1. Line contains only the equation (or minimal text)
        # 2. Equation is complex (contains fractions, multiple terms)
        # 3. Line starts with equation
        
        line_without_eq = line.replace(equation, '').strip()
        
        if len(line_without_eq) < 10:  # Minimal surrounding text
            return True
        
        if any(op in equation for op in ['/', '^', '_', '\\frac']):
            return True
        
        if line.strip().startswith(equation):
            return True
        
        return False
    
    def _clean_double_math(self, line: str) -> str:
        """Clean up double math formatting like $$x$$ -> $x$."""
        # Remove double dollar signs
        line = re.sub(r'\$\$([^$]+)\$\$', r'$\1$', line)
        
        # Remove nested math formatting
        line = re.sub(r'\$\$([^$]*)\$([^$]*)\$\$', r'$\1\2$', line)
        
        return line
    
    def _restore_protected_math(self, content: str, math_blocks: Dict[str, str]) -> str:
        """Restore protected math blocks, converting \\[...\\] to $$...$$ for Pandoc compatibility."""
        for placeholder, original in math_blocks.items():
            # Convert \[...\] to $$...$$ for better Pandoc compatibility
            if original.startswith('\\[') and original.endswith('\\]'):
                # Extract content between \[ and \]
                math_content = original[2:-2].strip()
                restored = f"$${math_content}$$"
            else:
                restored = original
            content = content.replace(placeholder, restored)
        return content 