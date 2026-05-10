# Instagram OSINT Module
# Scrapes public Instagram profiles using the instaloader library.
# No login or API key needed — only works on public accounts.
# Private accounts will still return basic profile info (bio, followers)
# but no posts.

from modules.base import BaseModule

# Try importing instaloader — if it's not installed, the module returns a helpful error
try:
    import instaloader
    _INSTALOADER_OK = True
except ImportError:
    _INSTALOADER_OK = False


class InstagramModule(BaseModule):
    """Fetches public Instagram profile data and recent posts."""

    name = "instagram"

    def run(self, target: dict) -> dict:
        username = target.get("username", "")

        if not username:
            return {"error": "No username provided — Instagram requires a handle."}
        if not _INSTALOADER_OK:
            return {"error": "instaloader not installed. Run: pip install instaloader"}

        try:
            # Set up instaloader in metadata-only mode (no file downloads)
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
                    pass  # rate-limited or unexpectedly private — return empty list

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
