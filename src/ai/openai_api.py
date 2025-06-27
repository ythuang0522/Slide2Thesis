import time
import logging
import base64
import io
from tenacity import retry, stop_after_attempt, wait_exponential
from openai import OpenAI
from PIL import Image
from typing import Optional
from .ai_api_interface import AIAPIInterface

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

class OpenAIAPI(AIAPIInterface):
    """Handles all interactions with the OpenAI API, including retries and rate limiting."""
    
    def __init__(self, api_key: str, model: str = "o4-mini-2025-04-16"):
        """Initialize the OpenAI API client.
        
        Args:
            api_key: The API key for authentication.
            model: The OpenAI model name to use (default: 'o4-mini-2025-04-16').
        """
        self.client = OpenAI(api_key=api_key)
        self.model = model
    
    @property
    def model_name(self) -> str:
        """Return the model name being used."""
        return self.model
    
    @property
    def provider_name(self) -> str:
        """Return the provider name."""
        return "openai"
    
    def _encode_image(self, image: Image.Image) -> str:
        """Encode PIL Image to base64 string for OpenAI API.
        
        Args:
            image: PIL Image object.
            
        Returns:
            Base64 encoded image string.
        """
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG')
        image_bytes = buffer.getvalue()
        return base64.b64encode(image_bytes).decode('utf-8')
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def generate_content(self, prompt: str, image: Optional[Image.Image] = None) -> Optional[str]:
        """Generate content using the OpenAI API with retry logic.
        
        Args:
            prompt: The text prompt for content generation.
            image: Optional PIL Image object to include in the generation.
            
        Returns:
            Generated text content or None if generation fails.
        """
        try:
            if image:
                base64_image = self._encode_image(image)
                input_data = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": prompt},
                            {"type": "input_image", "image_url": f"data:image/jpeg;base64,{base64_image}"},
                        ],
                    }
                ]
                response = self.client.responses.create(
                    model=self.model,
                    input=input_data,
                )
                output_text = getattr(response, 'output_text', None)

                return output_text
            else:
                # Text-only message (fallback to chat.completions.create for text-only)
                messages = [
                    {"role": "user", "content": prompt}
                ]
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                )
                time.sleep(1)
                return response.choices[0].message.content if response.choices else None
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise 