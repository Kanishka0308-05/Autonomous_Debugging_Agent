import os
import json
import time
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger("LLM_Utility")

# Tried in order. Models that are retired (404) or out of quota (429) are skipped
# for a while so later calls don't waste time on them.
MODELS_TO_TRY = [
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


def get_api_key():
    """Retrieve Gemini API Key from environment."""
    return os.getenv("GEMINI_API_KEY", "").strip()

def is_gemini_available() -> bool:
    """Check if a valid Gemini API key is configured."""
    key = get_api_key()
    return bool(key and key != "your_gemini_api_key_here")


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


def call_gemini(prompt: str, system_instruction: str = "") -> str:
    """
    Call the Gemini API (google-genai SDK) with per-request timeouts.
    Tries the available models in order and returns None if none respond in time,
    so callers can fall back to rule-based logic.
    """
    api_key = get_api_key()
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

    for model_name in MODELS_TO_TRY:
        if _model_skip_until.get(model_name, 0) > time.time():
            continue
        for attempt in range(2):  # one quick retry for transient 503s
            if time.time() > deadline:
                logger.warning("Gemini call budget exhausted. Operating in Mock Mode.")
                return None
            try:
                response = client.models.generate_content(model=model_name, contents=full_prompt)
                if response and response.text:
                    return response.text
                break
            except Exception as m_err:
                kind = _failure_kind(m_err)
                logger.debug(f"Model {model_name} failed ({kind}): {m_err}")
                if kind == "503" and attempt == 0:
                    time.sleep(1)
                    continue
                if kind in MODEL_COOLDOWN_S:
                    _model_skip_until[model_name] = time.time() + MODEL_COOLDOWN_S[kind]
                break

    logger.warning("All Gemini model attempts failed. Operating in Mock Mode.")
    return None
