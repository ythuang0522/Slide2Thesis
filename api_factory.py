import os
import logging
from typing import Optional
from ai_api_interface import AIAPIInterface
from gemini_api import GeminiAPI
from openai_api import OpenAIAPI

logger = logging.getLogger(__name__)

def detect_provider_from_model(model: str) -> str:
    """Detect the API provider based on model name patterns.
    
    Args:
        model: The model name.
        
    Returns:
        Provider name ('gemini' or 'openai').
    """
    model_lower = model.lower()
    
    if model_lower.startswith('gemini'):
        return 'gemini'
    elif model_lower.startswith(('gpt', 'o1')):
        return 'openai'
    else:
        # Default to gemini for unknown patterns
        logger.warning(f"Unknown model pattern '{model}', defaulting to Gemini")
        return 'gemini'

def create_ai_api(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    gemini_api_key: Optional[str] = None,
    openai_api_key: Optional[str] = None,
    api_key: Optional[str] = None  # Backward compatibility
) -> AIAPIInterface:
    """Create an AI API instance based on provider and model.
    
    Args:
        provider: API provider ('gemini', 'openai', or 'auto'). If None, auto-detect from model.
        model: Model name. If None, use default for the provider.
        gemini_api_key: Gemini API key.
        openai_api_key: OpenAI API key.
        api_key: Legacy API key (used as gemini_api_key for backward compatibility).
        
    Returns:
        AIAPIInterface instance.
        
    Raises:
        ValueError: If provider/model combination is invalid or API key is missing.
    """
    # Handle backward compatibility
    if api_key and not gemini_api_key:
        gemini_api_key = api_key
    
    # Get API keys from environment if not provided
    gemini_api_key = gemini_api_key or os.getenv('GEMINI_API_KEY')
    openai_api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
    
    # Auto-detect provider if not specified
    if provider is None or provider == 'auto':
        if model:
            provider = detect_provider_from_model(model)
        else:
            # Default to gemini if no model specified
            provider = 'gemini'
    
    # Set default models if not specified
    if model is None:
        default_models = get_default_models()
        model = default_models.get(provider)
        if model is None:
            raise ValueError(f"Unknown provider: {provider}")
    
    # Create the appropriate API instance
    if provider == 'gemini':
        if not gemini_api_key:
            raise ValueError("Gemini API key is required for Gemini provider")
        return GeminiAPI(api_key=gemini_api_key, model=model)
    
    elif provider == 'openai':
        if not openai_api_key:
            raise ValueError("OpenAI API key is required for OpenAI provider")
        return OpenAIAPI(api_key=openai_api_key, model=model)
    
    else:
        raise ValueError(f"Unsupported provider: {provider}")

def get_available_providers() -> list[str]:
    """Get list of available API providers.
    
    Returns:
        List of provider names.
    """
    return ['gemini', 'openai']

def get_default_models() -> dict[str, str]:
    """Get default models for each provider.
    
    Returns:
        Dictionary mapping provider names to default model names.
    """
    return {
        'gemini': 'gemini-2.5-pro-preview-06-05',
        'openai': 'gpt-4.1'
    } 