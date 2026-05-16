# LinkedIn Profile Scraper
# Opens a Chrome browser, waits for you to sign in to LinkedIn manually,
# then navigates to the target profile URL and scrapes it.
# No credentials stored anywhere — you just log in in the browser window.

import time
from modules.base import BaseModule

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from webdriver_manager.chrome import ChromeDriverManager


def _build_driver() -> webdriver.Chrome:
    """Launch a visible Chrome window with anti-detection flags."""
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
    # Remove the navigator.webdriver flag that LinkedIn uses to detect bots
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"},
    )
    return driver


def _wait_for_login(driver, timeout: int = 300) -> None:
    """
    Open the LinkedIn login page and wait for the user to sign in.
    Times out after `timeout` seconds (default 5 minutes).
    """
    driver.get("https://www.linkedin.com/login")
    print("[LinkedIn] Browser open — please sign in to LinkedIn in the window.")
    print(f"[LinkedIn] Waiting up to {timeout // 60} minutes...")

    # Wait until the URL no longer looks like the login/signup/authwall pages
    WebDriverWait(driver, timeout).until(
        lambda d: not any(
            x in d.current_url
            for x in ["login", "signup", "authwall", "checkpoint"]
        )
    )
    print("[LinkedIn] Signed in — proceeding to target profile.")


def _text(driver, selector: str, default: str = "") -> str:
    """Safely get text from the first element matching a CSS selector."""
    try:
        return driver.find_element(By.CSS_SELECTOR, selector).text.strip()
    except Exception:
        return default


def _scrape_posts(driver, profile_url: str) -> list:
    """Navigate to the recent-activity page and return the last 3 original posts."""
    base_url = profile_url.rstrip("/").split("?")[0]
    driver.get(f"{base_url}/recent-activity/all/")
    time.sleep(3)

    driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
    time.sleep(2)

    posts = []
    try:
        containers = driver.find_elements(By.CSS_SELECTOR, "div.feed-shared-update-v2")

        for container in containers[:10]:
            if len(posts) >= 3:
                break

            # Post text — try several selectors LinkedIn has used over time
            text = ""
            for sel in [
                ".feed-shared-text span[dir='ltr']",
                ".feed-shared-update-v2__description span[dir]",
                ".update-components-text span[dir]",
                ".break-words span[dir]",
            ]:
                try:
                    els = container.find_elements(By.CSS_SELECTOR, sel)
                    if els:
                        text = els[0].text.strip()
                        if text:
                            break
                except Exception:
                    continue

            if not text:
                continue

            # Post date
            date = ""
            for sel in [
                ".feed-shared-actor__sub-description span[aria-hidden='true']",
                ".update-components-actor__sub-description span[aria-hidden='true']",
            ]:
                try:
                    els = container.find_elements(By.CSS_SELECTOR, sel)
                    if els:
                        date = els[0].text.strip()
                        if date:
                            break
                except Exception:
                    continue

            # Reaction count
            likes = ""
            for sel in [
                ".social-details-social-counts__reactions-count",
                "button.react-button span",
            ]:
                try:
                    els = container.find_elements(By.CSS_SELECTOR, sel)
                    if els:
                        likes = els[0].text.strip()
                        if likes:
                            break
                except Exception:
                    continue

            posts.append({"text": text, "date": date, "likes": likes})
    except Exception:
        pass

    return posts


def _scrape_profile(driver, url: str) -> dict:
    """Navigate to the LinkedIn profile URL and extract all visible sections."""
    driver.get(url)
    time.sleep(3)

    # Scroll to the bottom and back to trigger all lazy-loaded sections
    for _ in range(5):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1.5)
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(1)

    # ── Profile header ─────────────────────────────────────────────────────
    name     = _text(driver, "h1")
    headline = _text(driver, "div.text-body-medium.break-words")

    location = ""
    loc_els = driver.find_elements(
        By.CSS_SELECTOR, "span.text-body-small.inline.t-black--light.break-words"
    )
    if loc_els:
        location = loc_els[0].text.strip()

    connections = ""
    for el in driver.find_elements(By.CSS_SELECTOR, "span.t-bold"):
        txt = el.text.lower()
        if "connection" in txt or "follower" in txt:
            connections = el.text.strip()
            break

    # ── About section ──────────────────────────────────────────────────────
    about = ""
    # Try to expand "see more" so we get the full text
    try:
        btns = driver.find_elements(
            By.CSS_SELECTOR, "section:has(#about) button.inline-show-more-text__button"
        )
        if btns:
            btns[0].click()
            time.sleep(0.5)
    except Exception:
        pass

    for sel in [
        "#about ~ div .inline-show-more-text--is-expanded",
        "#about ~ div .pv-about__summary-text",
        "#about + div div div div span[aria-hidden='true']",
    ]:
        about = _text(driver, sel)
        if about:
            break

    # ── Experience section ─────────────────────────────────────────────────
    experience = []
    try:
        items = driver.find_elements(
            By.CSS_SELECTOR, "#experience ~ div .pvs-list__item--line-separated"
        )
        for item in items[:8]:
            bold   = item.find_elements(By.CSS_SELECTOR, "span.mr1.t-bold span[aria-hidden='true']")
            normal = item.find_elements(By.CSS_SELECTOR, "span.t-14.t-normal span[aria-hidden='true']")
            light  = item.find_elements(By.CSS_SELECTOR, "span.t-14.t-normal.t-black--light span[aria-hidden='true']")

            title   = bold[0].text.strip()   if bold   else ""
            company = normal[0].text.strip() if normal else ""
            dates   = light[0].text.strip()  if light  else ""

            if title or company:
                experience.append({"title": title, "company": company, "dates": dates})
    except Exception:
        pass

    # ── Education section ──────────────────────────────────────────────────
    education = []
    try:
        items = driver.find_elements(
            By.CSS_SELECTOR, "#education ~ div .pvs-list__item--line-separated"
        )
        for item in items[:5]:
            bold   = item.find_elements(By.CSS_SELECTOR, "span.mr1.t-bold span[aria-hidden='true']")
            normal = item.find_elements(By.CSS_SELECTOR, "span.t-14.t-normal span[aria-hidden='true']")
            light  = item.find_elements(By.CSS_SELECTOR, "span.t-14.t-normal.t-black--light span[aria-hidden='true']")

            school = bold[0].text.strip()   if bold   else ""
            degree = normal[0].text.strip() if normal else ""
            dates  = light[0].text.strip()  if light  else ""

            if school:
                education.append({"school": school, "degree": degree, "dates": dates})
    except Exception:
        pass

    # ── Skills section ─────────────────────────────────────────────────────
    skills = []
    try:
        skill_els = driver.find_elements(
            By.CSS_SELECTOR, "#skills ~ div .mr1.t-bold span[aria-hidden='true']"
        )
        skills = [el.text.strip() for el in skill_els[:15] if el.text.strip()]
    except Exception:
        pass

    # ── Recent posts ───────────────────────────────────────────────────────
    posts = _scrape_posts(driver, url)

    return {
        "url":         url,
        "name":        name,
        "headline":    headline,
        "location":    location,
        "connections": connections,
        "about":       about,
        "experience":  experience,
        "education":   education,
        "skills":      skills,
        "posts":       posts,
    }


class LinkedInModule(BaseModule):
    """Scrapes a LinkedIn profile after the user signs in manually in the browser."""

    name = "linkedin"

    def run(self, target: dict) -> dict:
        linkedin_url = target.get("linkedin_url", "").strip()
        if not linkedin_url:
            return {"error": "No LinkedIn profile URL provided."}

        driver = _build_driver()
        try:
            _wait_for_login(driver)
            return _scrape_profile(driver, linkedin_url)
        except Exception as exc:
            return {"error": str(exc)}
        finally:
            driver.quit()
