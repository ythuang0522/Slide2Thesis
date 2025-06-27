# Slide2Thesis - AI-powered academic document generation

from .ai.ai_api_interface import AIAPIInterface
from .ai.gemini_api import GeminiAPI
from .ai.openai_api import OpenAIAPI
from .ai.api_factory import create_ai_api, get_available_providers, get_default_models

from .processors.text_extractor import TextExtractor
from .processors.page_classifier import PageClassifier
from .processors.chapter_generator import ChapterGenerator
from .processors.citation_generator import CitationGenerator
from .processors.figure_generator import FigureGenerator
from .processors.yaml_metadata_generator import YamlMetadataGenerator
from .processors.thesis_compiler import ThesisCompiler

from .utils.style_manager import StyleManager

__version__ = "1.0.0"

__all__ = [
    # AI API classes
    'AIAPIInterface',
    'GeminiAPI', 
    'OpenAIAPI',
    'create_ai_api',
    'get_available_providers',
    'get_default_models',
    
    # Processing classes
    'TextExtractor',
    'PageClassifier',
    'ChapterGenerator',
    'CitationGenerator',
    'FigureGenerator',
    'YamlMetadataGenerator',
    'ThesisCompiler',
    
    # Utility classes
    'StyleManager',
] 