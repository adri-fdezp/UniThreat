import time
import urllib.parse
from modules.base import BaseModule

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


# Queries to run per target field.  {name} / {username} / {email} filled at runtime.
NAME_QUERIES = [
    ("General",         '"{name}"'),
    ("LinkedIn",        '"{name}" site:linkedin.com'),
    ("Twitter / X",     '"{name}" site:twitter.com OR site:x.com'),
    ("Facebook",        '"{name}" site:facebook.com'),
    ("Instagram",       '"{name}" site:instagram.com'),
    ("GitHub",          '"{name}" site:github.com'),
    ("Reddit",          '"{name}" site:reddit.com'),
    ("ResearchGate",    '"{name}" site:researchgate.net'),
    ("Academia",        '"{name}" site:academia.edu'),
    ("News",            '"{name}" news'),
    ("Documents",       '"{name}" filetype:pdf OR filetype:doc'),
    ("Contact Info",    '"{name}" email OR phone OR contact'),
]
USERNAME_QUERIES = [
    ("Username General", '"{username}"'),
    ("Username Social",  '"{username}" site:twitter.com OR site:instagram.com OR site:reddit.com'),
]
EMAIL_QUERIES = [
    ("Email Search", '"{email}"'),
]

RESULTS_SELECTOR = "div.g, div.tF2Cxc, div.v7W49e, div.MjjYud > div"
WAIT_SELECTOR    = "div.g, #search, #rso"
CAPTCHA_SELECTOR = "form#captcha-form, #recaptcha, div.g-recaptcha, input#captcha"


def _build_driver() -> webdriver.Chrome:
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
    # Hide webdriver flag via JS
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"},
    )
    return driver


def _extract(el) -> dict | None:
    """Extract title, url, snippet from a result element."""
    try:
        h3s = el.find_elements(By.TAG_NAME, "h3")
        title = h3s[0].text if h3s else ""

        links = el.find_elements(By.TAG_NAME, "a")
        url = ""
        for a in links:
            href = a.get_attribute("href") or ""
            if href.startswith("http") and "google.com" not in href:
                url = href
                break

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


def _search_one(driver, query: str, label: str, captcha_wait: int = 90) -> list[dict]:
    """Navigate to one Google search page and return extracted results."""
    encoded = urllib.parse.quote_plus(query)
    driver.get(f"https://www.google.com/search?q={encoded}&hl=en&num=20")
    time.sleep(1.5)

    # If CAPTCHA detected, wait for user to solve it manually
    if driver.find_elements(By.CSS_SELECTOR, CAPTCHA_SELECTOR):
        print(f"[Google] CAPTCHA detected on '{label}' — solve in browser ({captcha_wait}s timeout)")
        try:
            WebDriverWait(driver, captcha_wait).until_not(
                EC.presence_of_element_located((By.CSS_SELECTOR, CAPTCHA_SELECTOR))
            )
        except Exception:
            print(f"[Google] CAPTCHA timeout on '{label}', skipping")
            return [{"category": label, "error": "CAPTCHA timeout"}]

    # Wait for results
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, WAIT_SELECTOR))
        )
    except Exception:
        return []

    # Scroll to trigger lazy-loading
    for _ in range(2):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)

    results = []
    for el in driver.find_elements(By.CSS_SELECTOR, RESULTS_SELECTOR):
        data = _extract(el)
        if data:
            data["category"] = label
            results.append(data)

    time.sleep(1)  # polite delay between queries
    return results


class GoogleModule(BaseModule):
    """
    Google OSINT search module.

    Runs a visible (non-headless) Chrome session so the user can manually
    solve CAPTCHAs if Google blocks automated requests.  All queries share
    one browser session for efficiency.
    """

    name = "google"

    def run(self, target: dict) -> dict:
        name     = target.get("name", "")
        username = target.get("username", "")
        email    = target.get("email", "")

        queries: list[tuple[str, str]] = []
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
        all_results: list[dict] = []
        try:
            for label, q in queries:
                hits = _search_one(driver, q, label)
                all_results.extend(hits)
                print(f"[Google] {label}: {len(hits)} results")
        finally:
            driver.quit()

        return {"total": len(all_results), "results": all_results}
