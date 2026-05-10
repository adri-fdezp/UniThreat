# Shared Anthropic client — created once and reused for all API calls.
# This avoids opening a new connection every time a module runs.

import os
import anthropic
from dotenv import load_dotenv

load_dotenv()

_client = None


def get_client() -> anthropic.Anthropic:
    """Return the shared Anthropic client, creating it on first call."""
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is not set. "
                "Add it to backend/.env and restart."
            )
        _client = anthropic.Anthropic(api_key=api_key)
    return _client
