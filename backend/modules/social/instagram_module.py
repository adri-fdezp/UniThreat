"""
Instagram OSINT module.

Uses the ``instaloader`` library to retrieve publicly available data without
requiring an Instagram account, API key, or login credentials.
Only public information is collected — private accounts yield profile metadata
only (follower count, bio, etc.) and no post data.

Collects
--------
- Public profile  : full name, biography, follower/following counts,
                    post count, verification status, external URL,
                    business category
- Recent posts    : up to 15 most recent posts including caption text,
                    hashtags, mentions, geolocation, like count, and date

Note: Instagram applies rate-limiting to unauthenticated requests.
      If throttled, instaloader raises an exception which is caught and
      returned as ``{ "error": "..." }`` so the frontend can display it.

Required target field : ``username``
"""

from modules.base import BaseModule

try:
    import instaloader
    _INSTALOADER_OK = True
except ImportError:
    _INSTALOADER_OK = False


class InstagramModule(BaseModule):
    """OSINT module for public Instagram profiles.

    Attributes:
        name (str): Module identifier — ``"instagram"``.
    """

    name = "instagram"

    def run(self, target: dict) -> dict:
        """Fetch public Instagram profile and recent post data.

        Args:
            target: Dict with keys ``name``, ``username``, ``email``.
                    Only ``username`` is used by this module.

        Returns:
            Dict with profile and post data, or ``{"error": str}`` on failure.

            Keys on success:
                - ``username``, ``full_name``, ``biography``
                - ``followers``, ``following``, ``posts_count``
                - ``is_private``, ``is_verified``
                - ``external_url``, ``business_category``, ``profile_pic_url``
                - ``recent_posts`` — list of post dicts (empty if private)
        """
        username = target.get("username", "")

        if not username:
            return {"error": "No username provided — Instagram requires a handle."}
        if not _INSTALOADER_OK:
            return {"error": "instaloader not installed. Run: pip install instaloader"}

        try:
            # Initialise instaloader in metadata-only mode (no downloads)
            L = instaloader.Instaloader(
                quiet=True,
                download_pictures=False,
                download_videos=False,
                download_video_thumbnails=False,
                save_metadata=False,
                compress_json=False,
            )
            profile = instaloader.Profile.from_username(L.context, username)

            # Collect up to 15 recent posts for public accounts
            recent_posts = []
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
                except Exception:
                    pass  # Rate-limited or unexpectedly private — return empty list

            return {
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

        except Exception as exc:
            return {"error": str(exc)}
