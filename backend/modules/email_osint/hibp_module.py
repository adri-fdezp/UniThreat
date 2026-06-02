# Email OSINT Module
# Checks an email address from two angles:
#   1. Gravatar — looks up a public profile linked to the email (name, bio, linked accounts)
#   2. Holehe   — checks ~130 websites to see which ones this email is registered on

import hashlib
import os
import shutil
import subprocess
import sys
import requests
from modules.base import BaseModule


def _holehe_exe() -> str:
    """Find the holehe executable — prefer the one in the same venv as Python."""
    # Look beside the current Python executable first (works in venv)
    candidate = os.path.join(os.path.dirname(sys.executable), "holehe")
    if os.path.isfile(candidate) or os.path.isfile(candidate + ".exe"):
        return candidate
    # Fall back to whatever is on PATH
    found = shutil.which("holehe")
    if found:
        return found
    raise FileNotFoundError("holehe executable not found")


def _gravatar_lookup(email: str) -> dict:
    """
    Query the Gravatar API for a public profile linked to this email.
    Gravatar hashes emails with MD5 to identify profiles — no raw email is sent.
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
    """
    Run holehe as a subprocess to check which sites the email is registered on.
    We use subprocess so holehe's dependencies don't conflict with Flask's.
    Only lines starting with [+] are real hits — the rest are errors or skips.
    """
    try:
        proc = subprocess.run(
            [_holehe_exe(), "--only-used", "--no-clear", email],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
        )
        found_sites = []
        for line in proc.stdout.splitlines():
            stripped = line.strip()
            if stripped.startswith("[+]"):
                site = stripped[3:].strip()
                # Skip lines that are status messages (they contain @)
                if site and "@" not in site:
                    found_sites.append(site)
        return {"sites": found_sites, "error": None}
    except FileNotFoundError:
        return {"sites": [], "error": "holehe not installed. Run: pip install holehe"}
    except subprocess.TimeoutExpired:
        return {"sites": [], "error": "holehe timed out after 180s"}
    except Exception as exc:
        return {"sites": [], "error": str(exc)}


class EmailOsintModule(BaseModule):
    """Runs Gravatar and Holehe checks against the target's email address."""

    name = "email_osint"

    def run(self, target: dict) -> dict:
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
