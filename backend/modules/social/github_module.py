"""
GitHub OSINT module.

Uses the GitHub REST API (unauthenticated: 60 req/h; with token: 5000 req/h).
Set the GITHUB_TOKEN environment variable to avoid rate-limiting during demos.

Collects
--------
- Public profile  : bio, location, company, blog, Twitter handle, public email
- Repositories    : name, language, stars, topics, description, fork status (30 most recent)
- Commit emails   : email addresses extracted from commit metadata (5 repos × 10 commits)
- Organisations   : public organisation memberships
- Name search     : top 8 GitHub accounts matching the target's full name

Required target field : ``name``      — triggers a user search
Optional target field : ``username``  — triggers a full profile deep-dive
"""

import os
import requests
from modules.base import BaseModule


class GitHubModule(BaseModule):
    """OSINT module for the GitHub platform.

    Performs two levels of data collection depending on which target fields
    are provided:

    1. **Name search** (always, if ``name`` is set): queries the GitHub user
       search endpoint and returns the top 8 matching accounts.
    2. **Profile deep-dive** (only if ``username`` is set): fetches the full
       public profile, repository list, commit-extracted email addresses, and
       organisation memberships.

    Attributes:
        name (str): Module identifier — ``"github"``.
        BASE (str): GitHub REST API base URL.
    """

    name = "github"
    BASE = "https://api.github.com"

    def __init__(self):
        """Initialise HTTP headers.  Attach a token if GITHUB_TOKEN is set."""
        token = os.environ.get("GITHUB_TOKEN", "")
        self.headers = {
            "Accept":     "application/vnd.github.v3+json",
            "User-Agent": "UniThreat-OSINT/2.0",
        }
        if token:
            self.headers["Authorization"] = f"token {token}"

    def _get(self, url: str):
        """Make a GET request and return parsed JSON, or None on failure.

        Args:
            url: The full GitHub API URL to request.

        Returns:
            Parsed JSON object, or None if the request fails or returns non-200.
        """
        try:
            r = requests.get(url, headers=self.headers, timeout=15)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return None

    def run(self, target: dict) -> dict:
        """Execute GitHub OSINT gathering.

        Args:
            target: Dict with keys ``name``, ``username``, ``email``.

        Returns:
            Dict with keys:
                - ``profile``     — Profile dict or None
                - ``repos``       — List of repository dicts
                - ``emails``      — List of discovered email addresses
                - ``orgs``        — List of organisation dicts
                - ``name_search`` — List of user dicts from name-based search
        """
        name     = target.get("name", "")
        username = target.get("username", "")

        result = {
            "profile":     None,
            "repos":       [],
            "emails":      [],
            "name_search": [],
            "orgs":        [],
        }

        # ── Name-based user search ──────────────────────────────────────────
        if name:
            data = self._get(
                f"{self.BASE}/search/users?q={requests.utils.quote(name)}&per_page=8"
            )
            if data:
                result["name_search"] = [
                    {
                        "login":  u.get("login"),
                        "url":    u.get("html_url"),
                        "avatar": u.get("avatar_url"),
                        "type":   u.get("type"),
                    }
                    for u in data.get("items", [])
                ]

        # ── Full profile deep-dive (requires username) ──────────────────────
        if username:
            profile = self._get(f"{self.BASE}/users/{username}")
            if profile:
                result["profile"] = {
                    "login":            profile.get("login"),
                    "name":             profile.get("name"),
                    "email":            profile.get("email"),
                    "bio":              profile.get("bio"),
                    "company":          profile.get("company"),
                    "location":         profile.get("location"),
                    "blog":             profile.get("blog"),
                    "twitter_username": profile.get("twitter_username"),
                    "public_repos":     profile.get("public_repos"),
                    "followers":        profile.get("followers"),
                    "following":        profile.get("following"),
                    "created_at":       profile.get("created_at"),
                    "hireable":         profile.get("hireable"),
                    "avatar_url":       profile.get("avatar_url"),
                    "url":              profile.get("html_url"),
                }
                if profile.get("email"):
                    result["emails"].append(profile["email"])

            # Repositories (sorted by most recently updated, up to 30)
            repos = self._get(
                f"{self.BASE}/users/{username}/repos?sort=updated&per_page=30"
            ) or []
            result["repos"] = [
                {
                    "name":        r.get("name"),
                    "description": r.get("description"),
                    "url":         r.get("html_url"),
                    "stars":       r.get("stargazers_count"),
                    "language":    r.get("language"),
                    "topics":      r.get("topics", []),
                    "fork":        r.get("fork"),
                    "updated_at":  r.get("updated_at"),
                }
                for r in repos
            ]

            # Email addresses from commit metadata (5 repos × 10 commits)
            # noreply addresses are excluded as they are GitHub-generated aliases.
            emails_set = set(result["emails"])
            for repo in repos[:5]:
                commits = self._get(
                    f"{self.BASE}/repos/{username}/{repo['name']}/commits?per_page=10"
                ) or []
                if isinstance(commits, list):
                    for c in commits:
                        email = c.get("commit", {}).get("author", {}).get("email", "")
                        if email and "@" in email and "noreply" not in email:
                            emails_set.add(email)
            result["emails"] = list(emails_set)

            # Public organisation memberships
            orgs = self._get(f"{self.BASE}/users/{username}/orgs") or []
            result["orgs"] = [
                {"name": o.get("login"), "url": f"https://github.com/{o.get('login')}"}
                for o in orgs
            ]

        return result
