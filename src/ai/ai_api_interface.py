from abc import ABC, abstractmethod
from typing import Optional
from PIL import Image

class AIAPIInterface(ABC):
    """Abstract base class for AI API providers."""
    
    @abstractmethod
    def generate_content(self, prompt: str, image: Optional[Image.Image] = None) -> Optional[str]:
        """Generate content using the AI API.
        
        Args:
            prompt: The text prompt for content generation.
            image: Optional PIL Image object to include in the generation.
            
        Returns:
            Generated text content or None if generation fails.
        """
        pass
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model name being used."""
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name (e.g., 'gemini', 'openai')."""
        pass 