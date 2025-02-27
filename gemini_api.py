import time
import logging
from tenacity import retry, stop_after_attempt, wait_exponential
from google import genai
from PIL import Image
from typing import Optional, Union

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GeminiAPI:
    """Handles all interactions with the Gemini API, including retries and rate limiting."""
    
    def __init__(self, api_key: str):
        """Initialize the Gemini API client.
        
        Args:
            api_key: The API key for authentication.
        """
        self.client = genai.Client(api_key=api_key)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry_error_callback=lambda retry_state: None
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
                model="gemini-2.0-flash-exp",
                contents=contents
            )
            time.sleep(1)  # Avoid rate limiting
            return response.text if response.text else None
        except Exception as e:
            logger.error(f"Gemini API call failed: {e}")
            raise 