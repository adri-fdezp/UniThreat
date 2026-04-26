"""
Email OSINT module.

Performs two independent checks against an email address to discover linked
accounts and public profile data.

Gravatar lookup
---------------
Gravatar (gravatar.com) is a globally recognised avatar service widely used
by developers and bloggers.  The lookup works by hashing the email with MD5
and querying the Gravatar JSON API — no authentication needed.  A found
profile may link the email to a real name, biography, location, and
other social media accounts.

Holehe check
------------
`holehe` (pip install holehe) is an open-source tool that probes ~130 websites
(Instagram, Twitter, Adobe, Spotify, GitHub, Snapchat, etc.) to determine
whether the target email is registered.  It is run as a subprocess so that
its own dependency chain is isolated from the Flask process.  Only confirmed
registrations (lines starting with ``[+]``) are returned.

Required target field : ``email``
"""

import hashlib
import subprocess
import sys
import requests
from modules.base import BaseModule


def _gravatar_lookup(email: str) -> dict:
    """Query the Gravatar API for a public profile linked to the email.

    The email is hashed with MD5 (lowercase, stripped) as per the
    Gravatar specification — no raw email is transmitted.

    Args:
        email: Target email address.

    Returns:
        Dict with ``found=True`` and profile fields on success, or
        ``{"found": False}`` if no Gravatar profile exists.
    """
    h = hashlib.md5(email.lower().strip().encode()).hexdigest()
    try:
        r = requests.get(f"https://www.gravatar.com/{h}.json", timeout=10)
        if r.status_code == 200:
            entry = r.json().get("entry", [{}])[0]
            return {
                "found":        True,
                "display_name": entry.get("displayName"),
                "about_me":     entry.get("aboutMe"),
                "location":     entry.get("currentLocation"),
                "urls":         [u.get("value") for u in entry.get("urls", [])],
                "accounts":     [a.get("shortname") for a in entry.get("accounts", [])],
                "profile_url":  f"https://www.gravatar.com/{h}",
            }
    except Exception:
        pass
    return {"found": False}


def _holehe_check(email: str) -> dict:
    """Run holehe to check which sites the email is registered on.

    holehe is invoked as a subprocess using the same Python interpreter
    that is running the Flask server.  This avoids import conflicts and
    allows holehe's own dependencies to be isolated.

    Args:
        email: Target email address.

    Returns:
        Dict with keys:
            - ``sites`` (list[str]) — Site names where the email is registered
            - ``error`` (str|None)  — Error message, or None on success
    """
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "holehe", "--only-used", "--no-clear", email],
            capture_output=True,
            text=True,
            timeout=180,
        )
        found_sites = []
        for line in proc.stdout.splitlines():
            stripped = line.strip()
            # holehe marks confirmed registrations with [+]
            if stripped.startswith("[+]"):
                site = stripped[3:].strip()
                # Exclude lines that contain @ — these are status messages, not site names
                if site and "@" not in site:
                    found_sites.append(site)
        return {"sites": found_sites, "error": None}
    except FileNotFoundError:
        return {"sites": [], "error": "holehe not installed. Run: pip install holehe"}
    except subprocess.TimeoutExpired:
        return {"sites": [], "error": "holehe timed out after 180 s"}
    except Exception as exc:
        return {"sites": [], "error": str(exc)}


class EmailOsintModule(BaseModule):
    """OSINT module for email address intelligence gathering.

    Combines a Gravatar profile lookup with a multi-site registration check
    via holehe to identify where an email address is registered.

    Attributes:
        name (str): Module identifier — ``"email_osint"``.
    """

    name = "email_osint"

    def run(self, target: dict) -> dict:
        """Execute email OSINT checks.

        Args:
            target: Dict with keys ``name``, ``username``, ``email``.
                    Only ``email`` is used.

        Returns:
            Dict with keys:
                - ``email``              (str)  — The target email address
                - ``gravatar``           (dict) — Gravatar lookup result
                - ``site_registrations`` (list) — Sites where email is registered
                - ``holehe_error``       (str)  — holehe error message, or None
            Or ``{"error": str}`` if no email was provided.
        """
        email = target.get("email", "")
        if not email:
            return {"error": "No email address provided."}

        gravatar = _gravatar_lookup(email)
        holehe   = _holehe_check(email)

        return {
            "email":              email,
            "gravatar":           gravatar,
            "site_registrations": holehe["sites"],
            "holehe_error":       holehe["error"],
        }
