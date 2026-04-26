"""
Username enumeration module.

Uses the WhatsMyName (WMN) dataset — a community-maintained JSON registry of
500+ websites — to check whether a target username exists on each site.

Detection method
----------------
For each site in the dataset, the module:
    1. Constructs the profile URL using the site's ``uri_check`` template.
    2. Makes an HTTP GET request with a standard browser User-Agent.
    3. Checks whether the response HTTP status code matches ``e_code`` AND
       whether the ``e_string`` marker appears in the response body.
    4. If both conditions are met, the account is considered found.

Performance
-----------
All site checks run concurrently using a ``ThreadPoolExecutor`` (40 workers),
keeping total runtime under ~60 seconds for ~500 sites.
The WMN dataset is downloaded once and cached at module level for the lifetime
of the process — subsequent runs reuse the cached data.

Required target field : ``username``

Dataset source
--------------
https://github.com/WebBreacher/WhatsMyName
"""

import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from modules.base import BaseModule

WMN_DATA_URL = (
    "https://raw.githubusercontent.com/WebBreacher/WhatsMyName/main/wmn-data.json"
)

# Module-level cache — the dataset is ~500 KB and changes infrequently
_wmn_cache = None


def _load_wmn_data() -> dict:
    """Download and cache the WhatsMyName dataset.

    Returns:
        Parsed JSON dict from the WMN repository.

    Raises:
        requests.HTTPError: If the dataset cannot be retrieved.
    """
    global _wmn_cache
    if _wmn_cache is None:
        r = requests.get(WMN_DATA_URL, timeout=30)
        r.raise_for_status()
        _wmn_cache = r.json()
    return _wmn_cache


def _check_site(site: dict, username: str):
    """Check whether a username exists on a single site.

    Args:
        site:     One entry from the WMN ``sites`` array.
        username: The target username to probe.

    Returns:
        Dict ``{ site, category, url }`` if found, else ``None``.
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
    """OSINT module for cross-platform username enumeration.

    Attributes:
        name (str): Module identifier — ``"username_enum"``.
    """

    name = "username_enum"

    def run(self, target: dict) -> dict:
        """Check the target username against 500+ sites concurrently.

        Args:
            target: Dict with keys ``name``, ``username``, ``email``.
                    Only ``username`` is used.

        Returns:
            Dict with keys:
                - ``username``      (str)  — The checked username
                - ``total_found``   (int)  — Number of confirmed profiles
                - ``total_checked`` (int)  — Number of sites tested
                - ``by_category``   (dict) — Results grouped by site category
                - ``profiles``      (list) — All results sorted alphabetically
            Or ``{ "error": str }`` if ``username`` is missing or the dataset
            cannot be loaded.
        """
        username = target.get("username", "")
        if not username:
            return {"error": "No username provided for enumeration."}

        try:
            wmn = _load_wmn_data()
        except Exception as exc:
            return {"error": f"Could not load WhatsMyName dataset: {exc}"}

        sites = wmn.get("sites", [])
        found = []

        # Concurrent site checks — 40 workers balances speed vs. rate-limiting
        with ThreadPoolExecutor(max_workers=40) as executor:
            futures = {executor.submit(_check_site, s, username): s for s in sites}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    found.append(result)

        # Group results by site category (Social Media, Gaming, Coding, etc.)
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
