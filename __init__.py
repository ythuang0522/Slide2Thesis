# Slide2Thesis - AI-powered academic document generation
# This file provides backward compatibility by importing from the new src structure

from src.ai.ai_api_interface import AIAPIInterface
from src.ai.gemini_api import GeminiAPI
from src.ai.openai_api import OpenAIAPI
from src.ai.api_factory import create_ai_api, get_available_providers, get_default_models
from src.processors.text_extractor import TextExtractor
from src.processors.page_classifier import PageClassifier
from src.processors.chapter_generator import ChapterGenerator
from src.processors.yaml_metadata_generator import YamlMetadataGenerator
from src.processors.citation_generator import CitationGenerator
from src.processors.thesis_compiler import ThesisCompiler
from src.utils.style_manager import StyleManager

__all__ = [
    'AIAPIInterface',
    'GeminiAPI',
    'OpenAIAPI',
    'create_ai_api',
    'get_available_providers',
    'get_default_models',
    'TextExtractor',
    'PageClassifier',
    'ChapterGenerator',
    'YamlMetadataGenerator',
    'CitationGenerator',
    'ThesisCompiler',
    'StyleManager'
] 