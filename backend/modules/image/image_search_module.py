# Image Search Module
# Searches the web for images by the target's name, username, and email.
# No API key or login needed — uses the ddgs library, like the DuckDuckGo module.
# Results are merged and ranked by how well each image's source page matches the
# target. A match on the page says nothing about who the image actually shows.

from ddgs import DDGS
from modules.base import BaseModule
from modules.search.ranking import build_response

# Search engines ddgs queries for images, in the order it tries them
BACKENDS = "bing,duckduckgo"

# Most images to request for each query
MAX_RESULTS = 30


class ImageSearchModule(BaseModule):
    """Finds images on the web that are linked to the target's identifiers."""

    name = "image_search"

    def run(self, target: dict) -> dict:
        name     = target.get("name", "")
        username = target.get("username", "").lstrip("@")
        email    = target.get("email", "")

        queries = []
        if name:
            queries.append(("Name search", f'"{name}"'))
        if username:
            queries.append(("Alias search", f'"{username}"'))
        if email:
            queries.append(("Email search", f'"{email}"'))

        results = []
        with DDGS() as ddgs:
            for label, q in queries:
                try:
                    # Previews load on the graph by themselves, so explicit images stay filtered out
                    hits = ddgs.images(q, safesearch="off", max_results=MAX_RESULTS, backend=BACKENDS)
                except Exception as exc:
                    # ddgs raises when a query simply finds nothing, which isn't a failure
                    if "No results" not in str(exc):
                        results.append({"category": label, "error": str(exc)})
                    continue

                for position, h in enumerate(hits, start=1):
                    # Without both there's no picture to show or page to credit it to
                    if not h.get("url") or not h.get("image"):
                        continue
                    results.append({
                        "category":    label,
                        "title":       self._title(h),
                        "url":         h["url"],
                        "description": self._describe(h),
                        "position":    position,
                        "image":       h["image"],
                        "thumbnail":   h.get("thumbnail", ""),
                    })

        return build_response(results, target)

    def _title(self, hit: dict) -> str:
        """Use the image's title, or name its site when the engine returned only punctuation."""
        title = (hit.get("title") or "").strip()
        if any(char.isalnum() for char in title):
            return title
        return f"Image from {hit['source']}" if hit.get("source") else "Untitled image"

    def _describe(self, hit: dict) -> str:
        """Summarize an image's size and the site it came from."""
        parts = []
        if hit.get("width") and hit.get("height"):
            parts.append(f"{hit['width']} × {hit['height']} pixels")
        if hit.get("source"):
            parts.append(f"from {hit['source']}")
        return ", ".join(parts)
