"""
Reddit OSINT module.

Uses the Reddit public JSON API — no authentication or API key required.
A descriptive User-Agent is included to comply with Reddit's API terms.

Collects
--------
- Account profile  : karma breakdown (post/comment/total), account age,
                     email verification status, Reddit Gold / employee flags
- Submitted posts  : up to 50 most recent posts (title, subreddit, score,
                     permalink, self-text preview up to 300 characters)
- Comments         : up to 25 most recent comments — useful for identifying
                     writing style, opinions, interests, and language patterns
- Subreddit list   : all communities the user has posted or commented in
- Trophies         : Reddit achievement awards
- Name search      : top 8 Reddit accounts matching the target's full name

Optional target field : ``username`` — triggers profile deep-dive
Optional target field : ``name``     — triggers name-based account search
"""

import requests
from modules.base import BaseModule


class RedditModule(BaseModule):
    """OSINT module for the Reddit platform.

    Attributes:
        name    (str):  Module identifier — ``"reddit"``.
        HEADERS (dict): HTTP headers including the required User-Agent.
    """

    name    = "reddit"
    HEADERS = {"User-Agent": "UniThreat/2.0 OSINT Research (Academic Thesis)"}

    def _get(self, url: str):
        """Make a GET request to the Reddit JSON API.

        Args:
            url: Full Reddit JSON API URL (must end in ``.json``).

        Returns:
            Parsed JSON dict, or None if the request fails.
        """
        try:
            r = requests.get(url, headers=self.HEADERS, timeout=15)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return None

    def run(self, target: dict) -> dict:
        """Execute Reddit OSINT gathering.

        Args:
            target: Dict with keys ``name``, ``username``, ``email``.

        Returns:
            Dict with keys:
                - ``profile``     — Account profile dict or None
                - ``posts``       — List of post dicts
                - ``comments``    — List of comment dicts
                - ``subreddits``  — Sorted list of active community names
                - ``name_search`` — List of user dicts from name-based search
                - ``trophies``    — List of trophy name strings
        """
        username = target.get("username", "")
        name     = target.get("name", "")

        result = {
            "profile":     None,
            "posts":       [],
            "comments":    [],
            "subreddits":  [],
            "name_search": [],
            "trophies":    [],
        }

        # ── Username-based deep dive ────────────────────────────────────────
        if username:
            # Account profile
            about = self._get(f"https://www.reddit.com/user/{username}/about.json")
            if about and "data" in about:
                d = about["data"]
                result["profile"] = {
                    "name":               d.get("name"),
                    "karma_post":         d.get("link_karma"),
                    "karma_comment":      d.get("comment_karma"),
                    "total_karma":        d.get("total_karma"),
                    "created_utc":        d.get("created_utc"),
                    "has_verified_email": d.get("has_verified_email"),
                    "is_employee":        d.get("is_employee"),
                    "is_gold":            d.get("is_gold"),
                    "icon_img":           d.get("icon_img"),
                    "url":                f"https://reddit.com/user/{username}",
                }

            # Submitted posts (up to 50)
            posts_raw   = self._get(
                f"https://www.reddit.com/user/{username}/submitted.json?limit=50"
            )
            subreddits  = set()
            if posts_raw:
                for p in posts_raw.get("data", {}).get("children", []):
                    pd  = p.get("data", {})
                    sub = pd.get("subreddit", "")
                    subreddits.add(sub)
                    result["posts"].append({
                        "title":       pd.get("title"),
                        "subreddit":   sub,
                        "url":         f"https://reddit.com{pd.get('permalink', '')}",
                        "score":       pd.get("score"),
                        "created_utc": pd.get("created_utc"),
                        "selftext":    (pd.get("selftext") or "")[:300],
                    })
            result["subreddits"] = sorted(subreddits)

            # Comments — up to 25 most recent.
            # Comments are especially valuable for OSINT: they often reveal
            # interests, knowledge level, opinions, and writing patterns.
            comments_raw = self._get(
                f"https://www.reddit.com/user/{username}/comments.json?limit=50"
            )
            if comments_raw:
                for c in comments_raw.get("data", {}).get("children", [])[:25]:
                    cd = c.get("data", {})
                    subreddits.add(cd.get("subreddit", ""))
                    result["comments"].append({
                        "body":        (cd.get("body") or "")[:500],
                        "subreddit":   cd.get("subreddit"),
                        "score":       cd.get("score"),
                        "created_utc": cd.get("created_utc"),
                        "url":         f"https://reddit.com{cd.get('permalink', '')}",
                    })

            # Reddit trophies (achievement awards)
            trophies_raw = self._get(
                f"https://www.reddit.com/user/{username}/trophies.json"
            )
            if trophies_raw and "data" in trophies_raw:
                result["trophies"] = [
                    t.get("data", {}).get("name")
                    for t in trophies_raw["data"].get("trophies", [])
                    if t.get("data", {}).get("name")
                ]

        # ── Name-based account search ───────────────────────────────────────
        if name:
            search = self._get(
                f"https://www.reddit.com/search.json"
                f"?q={requests.utils.quote(name)}&type=user&limit=8"
            )
            if search:
                result["name_search"] = [
                    {
                        "name":  u.get("data", {}).get("name"),
                        "karma": u.get("data", {}).get("total_karma"),
                        "url":   f"https://reddit.com/user/{u.get('data', {}).get('name', '')}",
                    }
                    for u in search.get("data", {}).get("children", [])
                ]

        return result
