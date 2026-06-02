# DuckDuckGo Search Module
# Runs a set of targeted search queries (dorks) against DuckDuckGo.
# No API key or login needed — uses the ddgs library.
# Covers: social media, documents, contact info, news, images, and more.

from modules.base import BaseModule
from ddgs import DDGS


class DuckDuckGoModule(BaseModule):
    """Runs dork-style searches on DuckDuckGo and returns categorised results."""

    name = "duckduckgo"

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
