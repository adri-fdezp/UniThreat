# Google Search Module
# Opens a real Chrome browser (not headless) and runs searches on Google.
# Using a visible browser lets the user solve CAPTCHAs manually if Google blocks us.
# All queries share one browser session to avoid repeated startups.
# Results from every query are merged and ranked, so the best matches come first.

import time
import urllib.parse

import requests
from modules.base import BaseModule
from modules.search.ranking import build_response, url_key

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


# CSS selectors for different parts of the Google results page
# (div.v7W49e is left out: it wraps the whole result list, not a single result)
RESULTS_SELECTOR = "div.g, div.tF2Cxc, div.MjjYud > div"
WAIT_SELECTOR    = "div.g, #search, #rso"
CAPTCHA_SELECTOR = "form#captcha-form, #recaptcha, div.g-recaptcha, input#captcha"

CAPTCHA_ERROR = "Google showed a CAPTCHA that wasn't solved in time"

# Google wraps result links in an encrypted redirect (google.com/goto?url=...)
REDIRECT_LINK = "google.com/goto?"

# Search query templates — {name}, {username}, {email} are filled at runtime
NAME_QUERIES = [
    ("General",      '"{name}"'),
    ("LinkedIn",     '"{name}" site:linkedin.com'),
    ("Twitter / X",  '"{name}" site:twitter.com OR site:x.com'),
    ("Facebook",     '"{name}" site:facebook.com'),
    ("Instagram",    '"{name}" site:instagram.com'),
    ("GitHub",       '"{name}" site:github.com'),
    ("Reddit",       '"{name}" site:reddit.com'),
    ("ResearchGate", '"{name}" site:researchgate.net'),
    ("Academia",     '"{name}" site:academia.edu'),
    ("News",         '"{name}" news'),
    ("Documents",    '"{name}" filetype:pdf OR filetype:doc'),
    ("Contact Info", '"{name}" email OR phone OR contact'),
]
USERNAME_QUERIES = [
    ("Username General", '"{username}"'),
    ("Username Social",  '"{username}" site:twitter.com OR site:instagram.com OR site:reddit.com'),
]
EMAIL_QUERIES = [
    ("Email Search", '"{email}"'),
]


def _build_driver() -> webdriver.Chrome:
    """Launch Chrome with anti-detection flags so Google is less likely to block us."""
    opts = Options()
    opts.add_argument("--start-maximized")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    # Remove the navigator.webdriver flag that sites use to detect Selenium
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"},
    )
    return driver


def _extract(el) -> dict | None:
    """Pull title, link, and snippet text out of a single search result element."""
    try:
        # A result's title sits inside its link, which skips other links on the card
        # and unlinked headings like the knowledge panel's "Description"
        links = el.find_elements(By.XPATH, ".//a[.//h3]")
        if not links:
            return None
        title = links[0].find_element(By.TAG_NAME, "h3").text
        url = links[0].get_attribute("href") or ""
        if not url.startswith("http") or ("google.com" in url and REDIRECT_LINK not in url):
            return None

        # Try several snippet CSS classes — Google changes these frequently
        snippet = ""
        for sel in [".VwiC3b", ".st", ".aCOpRe", ".IsZvec", "div[data-sncf]"]:
            els = el.find_elements(By.CSS_SELECTOR, sel)
            if els and els[0].text:
                snippet = els[0].text
                break
        if not snippet and title:
            raw = el.text.replace(title, "").strip()
            snippet = raw[:300] + ("…" if len(raw) > 300 else "")

        if title and url:
            return {"title": title, "url": url, "description": snippet}
    except Exception:
        pass
    return None


def _resolve_link(url: str) -> str:
    """Read a wrapped link's real address from its redirect, without opening that page.

    Falls back to the wrapped link, which still opens the page but ranks less well.
    """
    if REDIRECT_LINK not in url:
        return url
    try:
        location = requests.get(url, allow_redirects=False, timeout=5).headers.get("Location", "")
    except requests.RequestException:
        return url
    # A block redirects back to google.com/sorry rather than to the result
    return location if location.startswith("http") and "google.com" not in location else url


def _search_one(driver, query: str, label: str, captcha_wait: int = 90) -> list:
    """Navigate to one Google search page and return all extracted results."""
    encoded = urllib.parse.quote_plus(query)
    driver.get(f"https://www.google.com/search?q={encoded}&hl=en&num=20")
    time.sleep(1.5)

    # If Google shows a CAPTCHA, wait for the user to solve it in the open browser window
    if driver.find_elements(By.CSS_SELECTOR, CAPTCHA_SELECTOR):
        print(f"[Google] CAPTCHA on '{label}' — solve in browser ({captcha_wait}s)")
        try:
            WebDriverWait(driver, captcha_wait).until_not(
                EC.presence_of_element_located((By.CSS_SELECTOR, CAPTCHA_SELECTOR))
            )
        except Exception:
            return [{"category": label, "error": CAPTCHA_ERROR}]

    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, WAIT_SELECTOR))
        )
    except Exception:
        return [{
            "category": label,
            "error": f"No results page loaded (got '{driver.title}' at {driver.current_url})",
        }]

    # Scroll down to trigger lazy-loaded results
    for _ in range(2):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)

    # The selectors can match a result and its wrapper, so count each page only once.
    # Elements come back in page order, which gives us Google's own ranking.
    results = []
    seen = set()
    for el in driver.find_elements(By.CSS_SELECTOR, RESULTS_SELECTOR):
        data = _extract(el)
        # Checking the raw link first avoids resolving the same result twice
        if not data or data["url"] in seen:
            continue
        seen.add(data["url"])

        data["url"] = _resolve_link(data["url"])
        if url_key(data["url"]) not in seen:
            seen.add(url_key(data["url"]))
            data["category"] = label
            data["position"] = len(results) + 1
            results.append(data)

    # Linked headings we couldn't read mean Google's layout changed, not that nothing was found
    if not results:
        headings = len(driver.find_elements(By.CSS_SELECTOR, "a h3"))
        if headings:
            return [{
                "category": label,
                "error": f"Couldn't read the {headings} results on the page — Google's layout may have changed",
            }]

    time.sleep(1)  # small delay between queries to avoid rate-limiting
    return results


class GoogleModule(BaseModule):
    """
    Google OSINT module using a visible Chrome browser.
    Runs one browser session for all queries — user can solve CAPTCHAs if they appear.
    """

    name = "google"

    def run(self, target: dict) -> dict:
        name     = target.get("name", "")
        username = target.get("username", "")
        email    = target.get("email", "")

        queries = []
        if name:
            for label, tmpl in NAME_QUERIES:
                queries.append((label, tmpl.format(name=name)))
        if username:
            for label, tmpl in USERNAME_QUERIES:
                queries.append((label, tmpl.format(username=username)))
        if email:
            for label, tmpl in EMAIL_QUERIES:
                queries.append((label, tmpl.format(email=email)))

        if not queries:
            return {"total": 0, "results": []}

        driver = _build_driver()
        all_results = []
        try:
            for label, q in queries:
                hits = _search_one(driver, q, label)
                all_results.extend(hits)
                print(f"[Google] {label}: {len(hits)} results")
                # Google blocks the whole browser, so later queries would each wait out a CAPTCHA too
                if any(hit.get("error") == CAPTCHA_ERROR for hit in hits):
                    break
        finally:
            driver.quit()

        return build_response(all_results, target)
