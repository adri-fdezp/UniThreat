import os
import anthropic

_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable is not set. "
                "Export it before starting the backend: export ANTHROPIC_API_KEY=sk-ant-..."
            )
        _client = anthropic.Anthropic(api_key=api_key)
    return _client
