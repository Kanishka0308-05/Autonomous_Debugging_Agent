import os
import json
import logging
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger("LLM_Utility")

def get_gemini_api_key() -> str:
    """Retrieve Gemini API Key from environment."""
    return os.getenv("GEMINI_API_KEY", "").strip()

def get_groq_api_key() -> str:
    """Retrieve Groq API Key from environment."""
    return os.getenv("GROQ_API_KEY", "").strip()

def get_api_key() -> str:
    """Backwards compatibility alias for Gemini API key."""
    return get_gemini_api_key()

def is_gemini_available() -> bool:
    """Check if a valid Gemini API key is configured."""
    key = get_gemini_api_key()
    return bool(key and key != "your_gemini_api_key_here")

def is_groq_available() -> bool:
    """Check if a valid Groq API key is configured."""
    key = get_groq_api_key()
    return bool(key and key != "your_groq_api_key_here")

def is_llm_available() -> bool:
    """Check if any configured LLM provider is available."""
    provider = os.getenv("LLM_PROVIDER", "auto").lower().strip()
    if provider == "gemini":
        return is_gemini_available()
    elif provider == "groq":
        return is_groq_available()
    else:  # auto / default fallback
        return is_gemini_available() or is_groq_available()

def get_active_llm_provider() -> str:
    """Return the currently active LLM provider name ('gemini', 'groq', or 'mock')."""
    provider_setting = os.getenv("LLM_PROVIDER", "auto").lower().strip()
    if provider_setting == "gemini" and is_gemini_available():
        return "gemini"
    elif provider_setting == "groq" and is_groq_available():
        return "groq"
    elif provider_setting in ("auto", ""):
        if is_gemini_available():
            return "gemini"
        elif is_groq_available():
            return "groq"
    return "mock"

def call_gemini(prompt: str, system_instruction: str = "") -> Optional[str]:
    """
    Call the Gemini API using Google Generative AI / GenAI SDK.
    Falls back gracefully if key is missing or call fails.
    """
    api_key = get_gemini_api_key()
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
        logger.warning(f"Gemini API call failed: {e}. Falling back to alternative/mock mode.")
        return None

def call_groq(prompt: str, system_instruction: str = "", model: str = None) -> Optional[str]:
    """
    Call the Groq API using official Groq SDK.
    Falls back gracefully if key is missing or call fails.
    """
    api_key = get_groq_api_key()
    if not is_groq_available():
        logger.info("GROQ_API_KEY missing or default. Operating in Mock Mode.")
        return None

    model_name = model or os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()

    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.2,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.warning(f"Groq API call failed: {e}. Falling back to alternative/mock mode.")
        return None

def call_llm(prompt: str, system_instruction: str = "") -> Optional[str]:
    """
    Centralized LLM router function.
    Calls Gemini or Groq based on LLM_PROVIDER setting and availability.
    Falls back: Gemini -> Groq -> None OR Groq -> Gemini -> None.
    Returning None signals agents to use their rule-based fallback mode.
    """
    provider_setting = os.getenv("LLM_PROVIDER", "auto").lower().strip()

    if provider_setting == "groq":
        res = call_groq(prompt, system_instruction)
        if res is not None:
            return res
        if is_gemini_available():
            logger.info("Groq provider call failed/unavailable. Falling back to Gemini.")
            return call_gemini(prompt, system_instruction)

    elif provider_setting == "gemini":
        res = call_gemini(prompt, system_instruction)
        if res is not None:
            return res
        if is_groq_available():
            logger.info("Gemini provider call failed/unavailable. Falling back to Groq.")
            return call_groq(prompt, system_instruction)

    else:  # "auto" or unspecified
        if is_gemini_available():
            res = call_gemini(prompt, system_instruction)
            if res is not None:
                return res
        if is_groq_available():
            logger.info("Gemini unavailable/failed. Falling back to Groq.")
            res = call_groq(prompt, system_instruction)
            if res is not None:
                return res

    logger.info("No LLM provider responded successfully. Operating in Mock Mode.")
    return None

