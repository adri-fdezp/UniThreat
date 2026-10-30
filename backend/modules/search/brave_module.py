# Brave Search Module
# Runs targeted search queries (dorks) through the official Brave Search API.
# No browser and no CAPTCHAs, but it needs BRAVE_API_KEY in backend/.env and
# every query uses paid API credit. Results come from Brave's own index, not Google's.

import html
import os
import re
import time

import requests
from dotenv import load_dotenv
from modules.base import BaseModule
from modules.search.ranking import build_response

load_dotenv()

API_URL = "https://api.search.brave.com/res/v1/web/search"
RESULTS_PER_QUERY = 20  # the most the API returns for one request

# Some plans only allow one request per second
REQUEST_DELAY = 1.1
RETRY_DELAY = 2

# Brave refuses every query with these, so there's no point sending the rest
AUTH_ERRORS = {401, 403}


def _clean(text: str) -> str:
    """Remove the <strong> highlighting Brave puts around matched words."""
    return html.unescape(re.sub(r"<[^>]+>", "", text or ""))


def _search(api_key: str, query: str) -> list:
    """Run one query and return the raw results, retrying once if rate-limited."""
    for attempt in range(2):
        response = requests.get(
            API_URL,
            headers={"Accept": "application/json", "X-Subscription-Token": api_key},
            params={"q": query, "count": RESULTS_PER_QUERY},
            timeout=15,
        )
        if response.status_code != 429 or attempt == 1:
            break
        time.sleep(RETRY_DELAY)

    response.raise_for_status()
    return response.json().get("web", {}).get("results", [])


class BraveModule(BaseModule):
    """Runs dork-style searches on Brave Search and returns categorised results."""

    name = "brave"

    # Query templates for searching by name.
    # {name} is replaced with the actual target name at runtime.
    NAME_QUERIES = [
        ("General",        '"{name}"'),
        ("LinkedIn",       '"{name}" site:linkedin.com'),
        ("Twitter / X",    '"{name}" site:twitter.com OR site:x.com'),
        ("Facebook",       '"{name}" site:facebook.com'),
        ("Instagram",      '"{name}" site:instagram.com'),
        ("GitHub",         '"{name}" site:github.com'),
        ("Reddit",         '"{name}" site:reddit.com'),
        ("YouTube",        '"{name}" site:youtube.com'),
        ("TikTok",         '"{name}" site:tiktok.com'),
        ("ResearchGate",   '"{name}" site:researchgate.net'),
        ("Academia",       '"{name}" site:academia.edu'),
        ("News / Press",   '"{name}" news article interview'),
        ("Documents",      '"{name}" filetype:pdf OR filetype:doc OR filetype:pptx'),
        ("Contact Info",   '"{name}" email OR phone OR contact OR address'),
        ("Images",         '"{name}" photo portrait'),
    ]

    # Query templates for searching by username.
    USERNAME_QUERIES = [
        ("Username General",   '"{username}"'),
        ("Username Social",    '"{username}" site:twitter.com OR site:instagram.com OR site:reddit.com OR site:tiktok.com'),
        ("Username GitHub",    '"{username}" site:github.com'),
        ("Username Twitch/YT", '"{username}" site:twitch.tv OR site:youtube.com'),
    ]

    def run(self, target: dict) -> dict:
        api_key = os.environ.get("BRAVE_API_KEY", "").strip()
        if not api_key:
            return {
                "error": (
                    "BRAVE_API_KEY is not set. "
                    "Add it to backend/.env and restart the backend."
                )
            }

        name     = target.get("name", "")
        username = target.get("username", "")
        email    = target.get("email", "")

        # Build the list of queries to run based on what fields were provided
        queries = []
        if name:
            for label, tmpl in self.NAME_QUERIES:
                queries.append((label, tmpl.format(name=name)))
        if username:
            for label, tmpl in self.USERNAME_QUERIES:
                queries.append((label, tmpl.format(username=username)))
        if email:
            queries.append(("Email Search", f'"{email}"'))

        results = []
        for index, (label, q) in enumerate(queries):
            if index:
                time.sleep(REQUEST_DELAY)
            try:
                for position, h in enumerate(_search(api_key, q), start=1):
                    # Without a URL there's nothing to open or tell apart from other hits
                    if not h.get("url"):
                        continue
                    results.append({
                        "category":    label,
                        "title":       _clean(h.get("title")),
                        "url":         h["url"],
                        "description": _clean(h.get("description")),
                        "position":    position,
                    })
            except requests.HTTPError as exc:
                status = exc.response.status_code
                if status in AUTH_ERRORS:
                    results.append({"category": label, "error": f"Brave rejected the API key (HTTP {status})"})
                    break
                results.append({"category": label, "error": f"Brave returned HTTP {status}"})
            except Exception as exc:
                results.append({"category": label, "error": str(exc)})

        return build_response(results, target)
