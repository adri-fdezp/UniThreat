# LinkedIn Profile Scraper
# Logs into LinkedIn with your personal account, then navigates to the target's
# profile URL and scrapes their public information.
#
# Credentials are read from environment variables:
#   LINKEDIN_EMAIL    — your LinkedIn login email
#   LINKEDIN_PASSWORD — your LinkedIn password
#
# The browser opens visibly so you can solve any security checks (2FA, CAPTCHA)
# manually if LinkedIn prompts them.

import os
import time
from modules.base import BaseModule

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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
    # Hide the webdriver flag so LinkedIn doesn't immediately block us
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"},
    )
    return driver


def _login(driver, email: str, password: str) -> None:
    """Log into LinkedIn. Waits up to 2 minutes for the user to solve any 2FA/CAPTCHA."""
    driver.get("https://www.linkedin.com/login")
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.ID, "username"))
    )

    driver.find_element(By.ID, "username").send_keys(email)
    driver.find_element(By.ID, "password").send_keys(password)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

    # Wait until we land on the feed, or a checkpoint (2FA / suspicious login check)
    WebDriverWait(driver, 30).until(
        lambda d: any(x in d.current_url for x in ["feed", "checkpoint", "/in/", "mynetwork"])
    )

    # If LinkedIn flagged the login, wait for the user to pass the check manually
    if "checkpoint" in driver.current_url:
        print("[LinkedIn] Security check — solve it in the browser window (up to 2 min)...")
        WebDriverWait(driver, 120).until(
            lambda d: "checkpoint" not in d.current_url
        )


def _text(driver, selector: str, default: str = "") -> str:
    """Safely get text from the first element matching a CSS selector."""
    try:
        return driver.find_element(By.CSS_SELECTOR, selector).text.strip()
    except Exception:
        return default


def _texts(driver, selector: str) -> list:
    """Get a list of text strings for all elements matching a CSS selector."""
    try:
        return [el.text.strip() for el in driver.find_elements(By.CSS_SELECTOR, selector) if el.text.strip()]
    except Exception:
        return []


def _scrape_profile(driver, url: str) -> dict:
    """Navigate to a LinkedIn profile URL and extract all visible sections."""
    driver.get(url)
    time.sleep(3)

    # Scroll to the bottom and back to trigger all lazy-loaded sections
    for _ in range(5):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1.5)
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(1)

    # ── Profile header ────────────────────────────────────────────────────────
    name     = _text(driver, "h1")
    headline = _text(driver, "div.text-body-medium.break-words")

    # Location sits in the top card below the headline
    location = ""
    loc_candidates = driver.find_elements(
        By.CSS_SELECTOR, "span.text-body-small.inline.t-black--light.break-words"
    )
    if loc_candidates:
        location = loc_candidates[0].text.strip()

    # Follower / connection count
    connections = ""
    for el in driver.find_elements(By.CSS_SELECTOR, "span.t-bold"):
        txt = el.text.lower()
        if "connection" in txt or "follower" in txt:
            connections = el.text.strip()
            break

    # ── About section ─────────────────────────────────────────────────────────
    about = ""
    # Try to expand the "see more" button first so we get the full text
    try:
        see_more_btns = driver.find_elements(
            By.CSS_SELECTOR, "section:has(#about) button.inline-show-more-text__button"
        )
        if see_more_btns:
            see_more_btns[0].click()
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

    # ── Experience section ────────────────────────────────────────────────────
    experience = []
    try:
        # Each experience item lives in a list under the #experience anchor
        items = driver.find_elements(
            By.CSS_SELECTOR, "#experience ~ div .pvs-list__item--line-separated"
        )
        for item in items[:8]:
            # LinkedIn uses aria-hidden spans to hold the visible text
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

    # ── Education section ─────────────────────────────────────────────────────
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

    # ── Skills section ────────────────────────────────────────────────────────
    skills = []
    try:
        skill_els = driver.find_elements(
            By.CSS_SELECTOR, "#skills ~ div .mr1.t-bold span[aria-hidden='true']"
        )
        skills = [el.text.strip() for el in skill_els[:15] if el.text.strip()]
    except Exception:
        pass

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
    }


class LinkedInModule(BaseModule):
    """Scrapes a LinkedIn profile after logging in with the researcher's account."""

    name = "linkedin"

    def run(self, target: dict) -> dict:
        linkedin_url = target.get("linkedin_url", "").strip()
        if not linkedin_url:
            return {"error": "No LinkedIn profile URL provided."}

        email    = os.environ.get("LINKEDIN_EMAIL", "")
        password = os.environ.get("LINKEDIN_PASSWORD", "")
        if not email or not password:
            return {
                "error": "LinkedIn credentials not set. "
                         "Add LINKEDIN_EMAIL and LINKEDIN_PASSWORD to backend/.env"
            }

        driver = _build_driver()
        try:
            _login(driver, email, password)
            return _scrape_profile(driver, linkedin_url)
        except Exception as exc:
            return {"error": str(exc)}
        finally:
            driver.quit()
