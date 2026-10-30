# Instagram OSINT Module
# Scrapes Instagram profiles using the instaloader library.
#
# Instagram now blocks anonymous (logged-out) profile lookups platform-wide —
# every unauthenticated request to the profile-lookup endpoint gets a 403,
# instaloader retries once, and the retry comes back 200 OK with an empty
# result set. That empty result is indistinguishable downstream from "this
# profile doesn't exist", so a session is required; there's no anonymous
# fallback worth keeping.
#
# One-time setup:
#   1. Log into the target Instagram account in Chrome (or Firefox/Edge/etc).
#   2. From backend/, with the venv active, run:
#        python -m instaloader --load-cookies=chrome --login=<your_ig_username>
#      (needs the `browser-cookie3` extra — already in requirements.txt)
#   3. Set INSTAGRAM_USERNAME=<your_ig_username> in backend/.env.
# This imports the session from your browser's cookies and stores it at
# instaloader's default session path, which this module loads automatically.

import os
import threading
from dotenv import load_dotenv
from modules.base import BaseModule

load_dotenv()

# Try importing instaloader — if it's not installed, the module returns a helpful error
try:
    import instaloader
    _INSTALOADER_OK = True
except ImportError:
    instaloader = None
    _INSTALOADER_OK = False

# Cache the authenticated Instaloader instance across requests — loading the
# session file from disk on every single run() call is wasteful, and modules
# run in parallel threads so this needs a lock rather than a bare dict check.
_session_cache: dict = {}
_session_lock = threading.Lock()


def _get_authenticated_loader(login_username: str):
    """Return a shared, session-authenticated Instaloader instance.

    Raises FileNotFoundError if no session file exists for this username yet.
    """
    assert instaloader is not None  # caller already checked _INSTALOADER_OK

    with _session_lock:
        if login_username in _session_cache:
            return _session_cache[login_username]

        L = instaloader.Instaloader(
            quiet=True,
            download_pictures=False,
            download_videos=False,
            download_video_thumbnails=False,
            save_metadata=False,
            compress_json=False,
            request_timeout=15,
        )
        session_file = os.environ.get("INSTAGRAM_SESSION_FILE") or None
        L.load_session_from_file(login_username, session_file)
        _session_cache[login_username] = L
        return L


class InstagramModule(BaseModule):
    """Fetches Instagram profile data and recent posts (requires a logged-in session)."""

    name = "instagram"

    def run(self, target: dict) -> dict:
        username = target.get("username", "")

        if not username:
            return {"error": "No username provided — Instagram requires a handle."}
        if not _INSTALOADER_OK:
            return {"error": "instaloader not installed. Run: pip install instaloader"}
        assert instaloader is not None  # narrows for the type checker; guard above proves it

        login_username = os.environ.get("INSTAGRAM_USERNAME", "").strip()
        if not login_username:
            return {
                "error": (
                    "Instagram blocks anonymous lookups now — a logged-in session "
                    "is required. Set INSTAGRAM_USERNAME in backend/.env (see the "
                    "setup steps in instagram_module.py)."
                )
            }

        try:
            L = _get_authenticated_loader(login_username)
        except FileNotFoundError:
            return {
                "error": (
                    f"No saved Instagram session found for '{login_username}'. "
                    f"Run: python -m instaloader --load-cookies=chrome "
                    f"--login={login_username} (with that account logged into "
                    "Chrome) to create one, then retry."
                )
            }
        except Exception as exc:
            return {"error": f"Failed to load Instagram session: {exc}"}

        try:
            profile = instaloader.Profile.from_username(L.context, username)

            # Collect up to 15 recent posts for public accounts
            recent_posts = []
            post_fetch_error = None
            if not profile.is_private:
                try:
                    for post in profile.get_posts():
                        if len(recent_posts) >= 15:
                            break
                        recent_posts.append({
                            "caption":  (post.caption or "")[:400],
                            "likes":    post.likes,
                            "location": str(post.location) if post.location else None,
                            "hashtags": list(post.caption_hashtags) if post.caption else [],
                            "mentions": list(post.caption_mentions) if post.caption else [],
                            "date":     post.date_utc.isoformat() if post.date_utc else None,
                            "is_video": post.is_video,
                            "url":      f"https://www.instagram.com/p/{post.shortcode}/",
                        })
                except Exception as post_exc:
                    post_fetch_error = str(post_exc)

            result = {
                "username":          profile.username,
                "full_name":         profile.full_name,
                "biography":         profile.biography,
                "followers":         profile.followers,
                "following":         profile.followees,
                "posts_count":       profile.mediacount,
                "is_private":        profile.is_private,
                "is_verified":       profile.is_verified,
                "external_url":      profile.external_url,
                "business_category": profile.business_category_name,
                "profile_pic_url":   profile.profile_pic_url,
                "recent_posts":      recent_posts,
            }
            if post_fetch_error:
                result["post_fetch_error"] = post_fetch_error
            return result

        except instaloader.exceptions.ProfileNotExistsException:
            return {"error": f"Instagram profile '{username}' not found."}
        except instaloader.exceptions.ConnectionException as exc:
            return {"error": f"Instagram blocked the request (rate-limited): {exc}"}
        except Exception as exc:
            return {"error": str(exc)}
