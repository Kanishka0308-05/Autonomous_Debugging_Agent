import os
import json
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger("LLM_Utility")

def get_api_key():
    """Retrieve Gemini API Key from environment."""
    return os.getenv("GEMINI_API_KEY", "").strip()

def is_gemini_available() -> bool:
    """Check if a valid Gemini API key is configured."""
    key = get_api_key()
    return bool(key and key != "your_gemini_api_key_here")

def call_gemini(prompt: str, system_instruction: str = "") -> str:
    """
    Call the Gemini API using Google Generative AI / GenAI SDK.
    Falls back to mock mode if key is missing or call fails.
    """
    api_key = get_api_key()
    if not is_gemini_available():
        logger.info("GEMINI_API_KEY missing or default. Operating in Mock Mode.")
        return None

    try:
        # Try google.genai or google.generativeai
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            full_prompt = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=full_prompt
            )
            return response.text
        except ImportError:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            full_prompt = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt
            response = model.generate_content(full_prompt)
            return response.text
    except Exception as e:
        logger.warning(f"Gemini API call failed: {e}. Falling back to mock/structured fallback mode.")
        return None
