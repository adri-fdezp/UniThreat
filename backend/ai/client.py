# Shared Anthropic client — created once and reused for all API calls.
# This avoids opening a new connection every time a module runs.

import os
import anthropic
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

_anthropic_client = None


def get_anthropic_client() -> anthropic.Anthropic:
    """Return the shared Anthropic client, creating it on first call."""
    global _anthropic_client
    if _anthropic_client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is not set. "
                "Add it to backend/.env and restart."
            )
        _anthropic_client = anthropic.Anthropic(api_key=api_key)
    return _anthropic_client


def get_gemini_client():
    """Configure and return the Gemini API (google-generativeai)."""
    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        raise ValueError(
            "GOOGLE_API_KEY is not set. "
            "Add it to backend/.env and restart."
        )
    genai.configure(api_key=api_key)
    return genai
