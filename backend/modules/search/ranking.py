# Search Result Ranking
# Shared by the Google and DuckDuckGo modules. Merges duplicate pages found by
# different queries and sorts the results so the best matches come first.
# Each hit needs: category, title, url, description, and position (its rank in
# the search engine's results for that query, starting at 1).

import re
import unicodedata
import urllib.parse

# Points for each ranking signal. An exact email, username, or LinkedIn URL says
# far more about who a page is about than a name, which other people can share.
SCORE_LINKEDIN_URL  = 60  # the exact profile URL the analyst supplied
SCORE_EMAIL         = 50  # email address appears in the title or snippet
SCORE_USERNAME_URL  = 40  # username is a whole part of the URL (github.com/<username>)
SCORE_USERNAME_TEXT = 25  # username appears in the title or snippet
SCORE_NAME_TITLE    = 30  # full name appears in the title
SCORE_NAME_SNIPPET  = 15  # full name appears only in the snippet
SCORE_NAME_WORDS    = 5   # every part of the name appears, but not as a phrase
SCORE_NAME_URL      = 15  # every part of the name appears in the URL path
SCORE_PROFILE_PAGE  = 20  # profile page, only counted if it also matches the target
SCORE_EXTRA_QUERY   = 5   # per additional query that found the same page (max 3)
SCORE_TOP_POSITION  = 10  # the engine's own rank: 10 for 1st place, 5 for 2nd, 2 for 5th...

# Profile pages on the platforms we search, matched against url_key() without its query
PROFILE_URL = re.compile(
    r"^(?:linkedin\.com/in/[^/]+"
    r"|(?:github\.com|x\.com|instagram\.com|facebook\.com|twitch\.tv)/(?P<handle>[^/]+)"
    r"|reddit\.com/(?:u|user)/[^/]+"
    r"|tiktok\.com/@[^/]+"
    r"|youtube\.com/(?:@[^/]+|(?:c|channel|user)/[^/]+)"
    r"|researchgate\.net/profile/[^/]+"
    r"|[^/]+\.academia\.edu(?:/[^/]+)?)$"
)
# Single-segment paths on those platforms that are site pages, not people
NON_PROFILE_PATHS = {
    "about", "directory", "explore", "groups", "hashtag", "help", "login", "marketplace",
    "pages", "privacy", "public", "search", "settings", "terms", "topics", "watch",
}

# URL query parameters that don't change what a page is about, ignored when spotting
# duplicates ("tab" is a view of the same profile, like github.com/<user>?tab=repositories)
TRACKING_PARAMS = {"fbclid", "gclid", "hl", "igshid", "ref", "si", "tab", "trk"}


def _fold(text: str) -> str:
    """Normalize case, accents, and spacing so 'Adrián  Pérez' matches 'adrian perez'."""
    decomposed = unicodedata.normalize("NFKD", text or "")
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(stripped.casefold().split())


def _has_term(term: str, text: str) -> bool:
    """Check for term as whole words, so 'ann' doesn't match 'joanna'."""
    return bool(term) and re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text) is not None


def url_key(url: str) -> str:
    """Reduce a URL to 'host/path?query' so variants of the same page compare equal."""
    try:
        parts = urllib.parse.urlsplit(url)
        host = parts.hostname or ""
        params = urllib.parse.parse_qsl(parts.query)
    except ValueError:
        return url.casefold()

    host = re.sub(r"^(?:www|m|mobile)\.", "", host)
    host = re.sub(r"^[a-z]{2}\.linkedin\.com$", "linkedin.com", host)  # dk.linkedin.com etc.
    if host == "twitter.com":
        host = "x.com"

    kept = [
        (k, v) for k, v in params
        if k.lower() not in TRACKING_PARAMS and not k.lower().startswith("utm_")
    ]
    query = urllib.parse.urlencode(kept)
    return f"{host}{parts.path.rstrip('/').casefold()}" + (f"?{query}" if query else "")


def _is_profile_page(address: str) -> bool:
    """Check whether a 'host/path' address is a person's page on a known platform."""
    match = PROFILE_URL.match(address)
    return bool(match) and match.group("handle") not in NON_PROFILE_PATHS


def _score(hit: dict, target: dict) -> float:
    """Score how likely a result is to be a useful page about the target."""
    name     = _fold(target.get("name", ""))
    username = _fold(target.get("username", "")).lstrip("@")
    email    = _fold(target.get("email", ""))
    linkedin = target.get("linkedin_url", "")

    title   = _fold(hit["title"])
    snippet = _fold(hit.get("description", ""))
    text    = f"{title} {snippet}"

    key = url_key(hit["url"])
    address = key.partition("?")[0]
    host, _, path = address.partition("/")
    path = _fold(urllib.parse.unquote(path))
    # Handles can carry an @ in the URL (tiktok.com/@name)
    url_parts = set(host.split(".")) | {part.lstrip("@") for part in path.split("/")}
    url_words = set(re.findall(r"[^\W_]+", path))  # split on _ too (/wiki/Jane_Doe)

    # Signals that tie the page to the target
    match = 0
    if linkedin and key == url_key(linkedin):
        match += SCORE_LINKEDIN_URL
    if _has_term(email, text):
        match += SCORE_EMAIL
    if username and username in url_parts:
        match += SCORE_USERNAME_URL
    elif _has_term(username, text):
        match += SCORE_USERNAME_TEXT

    name_words = name.split()
    if _has_term(name, title):
        match += SCORE_NAME_TITLE
    elif _has_term(name, snippet):
        match += SCORE_NAME_SNIPPET
    elif name_words and all(_has_term(word, text) for word in name_words):
        match += SCORE_NAME_WORDS
    # One-word names are skipped here, they turn up in too many unrelated URLs
    if len(name_words) > 1 and url_words.issuperset(name_words):
        match += SCORE_NAME_URL

    # A profile page only matters if it looks like the target's own
    if match and _is_profile_page(address):
        match += SCORE_PROFILE_PAGE

    extra_queries = min(len(hit["categories"]) - 1, 3)
    score = match + SCORE_EXTRA_QUERY * extra_queries + SCORE_TOP_POSITION / hit["position"]
    return round(score, 1)


def rank_results(hits: list, target: dict) -> list:
    """Merge duplicate pages across queries and sort the best matches first."""
    merged = {}
    errors = []
    for hit in hits:
        if "error" in hit:
            errors.append(hit)
            continue

        key = url_key(hit["url"])
        if key not in merged:
            merged[key] = {**hit, "categories": [hit["category"]]}
            continue

        # Same page again: keep the entry where the engine ranked it highest
        best = merged[key]
        categories = best["categories"]
        if hit["category"] not in categories:
            categories = categories + [hit["category"]]
        if hit["position"] < best["position"]:
            description = hit["description"] or best["description"]
            best = merged[key] = {**hit, "description": description}
        elif not best["description"]:
            best["description"] = hit["description"]
        best["categories"] = categories

    ranked = list(merged.values())
    for hit in ranked:
        hit["score"] = _score(hit, target)
    ranked.sort(key=lambda hit: (-hit["score"], hit["position"]))

    # Failed queries carry no result, so they go last and never push a hit down
    return ranked + errors


def build_response(hits: list, target: dict) -> dict:
    """Rank the hits into a module's return value, reporting a run where every query failed."""
    ranked = rank_results(hits, target)

    # With no hits at all, say why instead of reporting an empty search
    if ranked and all("error" in hit for hit in ranked):
        reasons = dict.fromkeys(hit["error"] for hit in ranked)
        return {"error": "; ".join(reasons), "total": 0, "results": ranked}

    return {"total": len(ranked), "results": ranked}
