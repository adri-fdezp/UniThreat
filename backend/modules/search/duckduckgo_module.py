"""
DuckDuckGo search OSINT module.

Uses the ``ddgs`` library (the official DuckDuckGo Search API wrapper,
formerly known as ``duckduckgo_search``) to run targeted dork-style queries
without authentication, API keys, or CAPTCHA challenges.

Collects
--------
Up to 8 results per query across 15+ query templates for ``name``:
    - General name search
    - Platform-specific dorks: LinkedIn, Twitter / X, Facebook, Instagram,
      GitHub, Reddit, YouTube, TikTok, ResearchGate, Academia.edu
    - Document search: PDF, DOC, PPTX
    - Contact information: email, phone, address
    - News and press appearances
    - Image / portrait search

4 additional query templates for ``username``:
    - General username search
    - Social media (Twitter, Instagram, Reddit, TikTok)
    - GitHub
    - Streaming (Twitch, YouTube)

1 additional query for ``email`` if provided.

Required target field : ``name``
Optional target fields: ``username``, ``email``
"""

from modules.base import BaseModule
from ddgs import DDGS


class DuckDuckGoModule(BaseModule):
    """OSINT module using DuckDuckGo Search.

    Runs a battery of targeted search queries (dorks) against DuckDuckGo
    and returns results categorised by query intent.

    Attributes:
        name           (str):  Module identifier — ``"duckduckgo"``.
        NAME_QUERIES   (list): Query templates that use the ``{name}`` field.
        USERNAME_QUERIES (list): Query templates that use ``{username}``.
    """

    name = "duckduckgo"

    # (label, query_template) — placeholders filled at runtime
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

    USERNAME_QUERIES = [
        ("Username General",   '"{username}"'),
        ("Username Social",    '"{username}" site:twitter.com OR site:instagram.com OR site:reddit.com OR site:tiktok.com'),
        ("Username GitHub",    '"{username}" site:github.com'),
        ("Username Twitch/YT", '"{username}" site:twitch.tv OR site:youtube.com'),
    ]

    def run(self, target: dict) -> dict:
        """Execute DuckDuckGo dork searches for the target.

        Args:
            target: Dict with keys ``name``, ``username``, ``email``.

        Returns:
            Dict with keys:
                - ``total``   (int)  — Total number of individual results
                - ``results`` (list) — List of dicts, each with:
                    ``category``, ``title``, ``url``, ``description``
                    (or ``error`` if the query failed)
        """
        name     = target.get("name", "")
        username = target.get("username", "")
        email    = target.get("email", "")

        # Build ordered list of (label, query) pairs
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
        with DDGS() as ddgs:
            for label, q in queries:
                try:
                    hits = list(ddgs.text(q, max_results=8))
                    for h in hits:
                        results.append({
                            "category":    label,
                            "title":       h.get("title", ""),
                            "url":         h.get("href", ""),
                            "description": h.get("body", ""),
                        })
                except Exception as exc:
                    results.append({"category": label, "error": str(exc)})

        return {"total": len(results), "results": results}
