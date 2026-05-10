# Username Enumeration Module
# Checks whether a username exists on 500+ websites using the WhatsMyName dataset.
# The dataset is a community-maintained JSON file that maps site names to
# the URL pattern and the string that appears when a profile is found.
#
# All site checks run in parallel (40 threads) to keep total time under ~60s.
# The dataset is cached in memory after the first download.

import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from modules.base import BaseModule

# WhatsMyName dataset — updated regularly by the community
WMN_DATA_URL = "https://raw.githubusercontent.com/WebBreacher/WhatsMyName/main/wmn-data.json"

# Cache the dataset after the first download so re-runs are instant
_wmn_cache = None


def _load_wmn_data() -> dict:
    """Download the WhatsMyName dataset (or return the cached copy)."""
    global _wmn_cache
    if _wmn_cache is None:
        r = requests.get(WMN_DATA_URL, timeout=30)
        r.raise_for_status()
        _wmn_cache = r.json()
    return _wmn_cache


def _check_site(site: dict, username: str):
    """
    Check if a username exists on one site.
    Returns a result dict if found, or None if not found / error.
    """
    url = site.get("uri_check", "").format(account=username)
    if not url:
        return None
    try:
        r = requests.get(
            url,
            timeout=8,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            allow_redirects=True,
        )
        # A profile is confirmed only if BOTH the status code and marker string match
        if (
            r.status_code == site.get("e_code", 200)
            and site.get("e_string", "") in r.text
        ):
            pretty = site.get("uri_pretty", url).format(account=username)
            return {
                "site":     site.get("name"),
                "category": site.get("cat", "other"),
                "url":      pretty,
            }
    except Exception:
        pass
    return None


class UsernameEnumerator(BaseModule):
    """Checks the target username against 500+ sites concurrently."""

    name = "username_enum"

    def run(self, target: dict) -> dict:
        username = target.get("username", "")
        if not username:
            return {"error": "No username provided for enumeration."}

        try:
            wmn = _load_wmn_data()
        except Exception as exc:
            return {"error": f"Could not load WhatsMyName dataset: {exc}"}

        sites = wmn.get("sites", [])
        found = []

        # Check all sites in parallel — 40 workers is a good balance of speed vs. rate limits
        with ThreadPoolExecutor(max_workers=40) as executor:
            futures = {executor.submit(_check_site, s, username): s for s in sites}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    found.append(result)

        # Group confirmed profiles by site category (Social, Gaming, Coding, etc.)
        by_category: dict[str, list] = {}
        for item in found:
            cat = item["category"]
            by_category.setdefault(cat, []).append(item)

        return {
            "username":      username,
            "total_found":   len(found),
            "total_checked": len(sites),
            "by_category":   by_category,
            "profiles":      sorted(found, key=lambda x: x["site"].lower()),
        }
