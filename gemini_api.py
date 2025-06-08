import time
import logging
from tenacity import retry, stop_after_attempt, wait_exponential
from google import genai
from google.genai import types
from PIL import Image
from typing import Optional, Union
from ai_api_interface import AIAPIInterface

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GeminiAPI(AIAPIInterface):
    """Handles all interactions with the Gemini API, including retries and rate limiting."""
    
    def __init__(self, api_key: str, model: str = "gemini-2.5-pro-preview-06-05"):
        """Initialize the Gemini API client.
        
        Args:
            api_key: The API key for authentication.
            model: The Gemini model name to use (default: 'gemini-2.5-pro-preview-06-05').
        """
        # Configure HTTP options with timeout in milliseconds
        http_options = types.HttpOptions(
            timeout=2 * 60 * 1000  # 2 minutes in milliseconds (180,000 ms)
        )
        self.client = genai.Client(api_key=api_key, http_options=http_options)
        self.model = model
    
    @property
    def model_name(self) -> str:
        """Return the model name being used."""
        return self.model
    
    @property
    def provider_name(self) -> str:
        """Return the provider name."""
        return "gemini"
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry_error_callback=lambda retry_state: logger.warning(f"Retrying API call, attempt {retry_state.attempt_number}")
    )
    def generate_content(self, prompt: str, image: Optional[Image.Image] = None) -> Optional[str]:
        """Generate content using the Gemini API with retry logic.
        
        Args:
            prompt: The text prompt for content generation.
            image: Optional PIL Image object to include in the generation.
            
        Returns:
            Generated text content or None if generation fails.
        """
        try:
            contents = [prompt]
            if image:
                contents.append(image)
            
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents
            )
            time.sleep(1)  # Avoid rate limiting
            return response.text if response.text else None
        except Exception as e:
            logger.error(f"Gemini API call failed: {e}")
            # For network-related errors, allow retry
            if "Server disconnected" in str(e) or "timeout" in str(e).lower():
                logger.warning("Network error detected, will retry if attempts remain")
                raise
            # For other errors, don't retry
            return None 