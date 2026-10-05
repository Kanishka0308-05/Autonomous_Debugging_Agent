import os
import json
import time
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

# Gemini models tried in order. Models that are retired (404) or out of quota (429) are
# skipped for a while so later calls don't waste time on them. Override with GEMINI_MODELS
# (comma-separated) in .env.
GEMINI_MODELS = [m.strip() for m in os.getenv("GEMINI_MODELS", "").split(",") if m.strip()] or [
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-flash-latest",
    "gemini-3-flash-preview",
    "gemini-3.5-flash-lite",
    "gemini-flash-lite-latest",
    "gemini-3.1-flash-lite",
]
REQUEST_TIMEOUT_S = 45      # per HTTP request
CALL_BUDGET_S = 120         # total time one call_gemini() may spend across models
MODEL_COOLDOWN_S = {"404": 24 * 3600, "429": 300, "503": 60, "504": 60, "timeout": 60}

_model_skip_until = {}


def _failure_kind(err: Exception) -> str:
    s = str(err)
    for code in ("404", "429", "503", "504"):
        if code in s:
            return code
    if "UNAVAILABLE" in s:
        return "503"
    if "timed out" in s.lower() or "timeout" in s.lower() or "deadline" in s.lower():
        return "timeout"
    return "other"


def call_gemini(prompt: str, system_instruction: str = "") -> Optional[str]:
    """
    Call the Gemini API (google-genai SDK) with per-request timeouts.
    Tries the available models in order and returns None if none respond in time,
    so callers can fall back to Groq or rule-based logic.
    """
    api_key = get_gemini_api_key()
    if not is_gemini_available():
        logger.info("GEMINI_API_KEY missing or default. Operating in Mock Mode.")
        return None

    full_prompt = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt
    deadline = time.time() + CALL_BUDGET_S

    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=api_key,
                              http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT_S * 1000))
    except Exception as e:
        logger.warning(f"google.genai client initialization error: {e}")
        return None

    for model_name in GEMINI_MODELS:
        if _model_skip_until.get(model_name, 0) > time.time():
            continue
        for attempt in range(2):  # one quick retry for transient 503s
            if time.time() > deadline:
                logger.warning("Gemini call budget exhausted. Falling back to alternative/mock mode.")
                return None
            try:
                response = client.models.generate_content(model=model_name, contents=full_prompt)
                if response and response.text:
                    return response.text
                break
            except Exception as m_err:
                kind = _failure_kind(m_err)
                logger.debug(f"Gemini model {model_name} failed ({kind}): {m_err}")
                if kind == "503" and attempt == 0:
                    time.sleep(1)
                    continue
                if kind in MODEL_COOLDOWN_S:
                    _model_skip_until[model_name] = time.time() + MODEL_COOLDOWN_S[kind]
                break

    logger.warning("All Gemini model attempts failed. Falling back to alternative/mock mode.")
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
        client = Groq(api_key=api_key, timeout=REQUEST_TIMEOUT_S)
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

