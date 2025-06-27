"""Processing modules for Slide2Thesis document generation pipeline."""

from .text_extractor import TextExtractor
from .page_classifier import PageClassifier
from .chapter_generator import ChapterGenerator
from .citation_generator import CitationGenerator
from .figure_generator import FigureGenerator
from .yaml_metadata_generator import YamlMetadataGenerator
from .thesis_compiler import ThesisCompiler

__all__ = [
    'TextExtractor',
    'PageClassifier', 
    'ChapterGenerator',
    'CitationGenerator',
    'FigureGenerator',
    'YamlMetadataGenerator',
    'ThesisCompiler',
] 