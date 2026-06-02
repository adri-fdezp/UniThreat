# LinkedIn Profile Scraper
# Opens a Chrome browser, waits for you to sign in to LinkedIn manually,
# then navigates to the target profile URL and scrapes it.
# No credentials stored anywhere — you just log in in the browser window.

import re
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
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"},
    )
    return driver


def _wait_for_login(driver, timeout: int = 300) -> None:
    """Open the LinkedIn login page and wait for the user to sign in."""
    driver.get("https://www.linkedin.com/login")
    print("[LinkedIn] Browser open — please sign in to LinkedIn in the window.")
    print(f"[LinkedIn] Waiting up to {timeout // 60} minutes...")
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


def _parse_date_range(raw: str) -> dict:
    """
    Split 'Jan 2020 – Present · 4 yrs 5 mos' into structured parts.
    LinkedIn uses both '–' (en dash) and '-' (hyphen) in date ranges.
    Returns: { start, end, duration }
    """
    if not raw:
        return {"start": "", "end": "", "duration": ""}

    # Separate the duration suffix (after · or •)
    parts = re.split(r"\s*[·•]\s*", raw, maxsplit=1)
    range_part = parts[0].strip()
    duration   = parts[1].strip() if len(parts) > 1 else ""

    # Split start / end on ' – ' or ' - '
    sep = re.search(r"\s+[–\-]\s+", range_part)
    if sep:
        start = range_part[: sep.start()].strip()
        end   = range_part[sep.end() :].strip()
    else:
        start = range_part
        end   = ""

    return {"start": start, "end": end, "duration": duration}


def _extract_role(item) -> dict:
    """
    Pull title, company, date, location, and description out of a single
    experience list item. Works for both top-level simple items and nested
    role items inside a grouped (multi-role) entry.
    """
    bold     = item.find_elements(By.CSS_SELECTOR, "span.mr1.t-bold span[aria-hidden='true']")
    normal   = item.find_elements(By.CSS_SELECTOR, "span.t-14.t-normal span[aria-hidden='true']")
    light    = item.find_elements(By.CSS_SELECTOR, "span.t-14.t-normal.t-black--light span[aria-hidden='true']")
    desc_els = item.find_elements(By.CSS_SELECTOR, ".pvs-list__outer-container .t-14.t-normal span[aria-hidden='true']")

    title    = bold[0].text.strip()    if bold              else ""
    company  = normal[0].text.strip()  if normal            else ""
    date_raw = light[0].text.strip()   if light             else ""
    location = light[1].text.strip()   if len(light) > 1   else ""

    # description: pick the first desc span whose text isn't already the date/location
    desc = ""
    for el in desc_els:
        candidate = el.text.strip()
        if candidate and candidate not in (date_raw, location, title, company):
            desc = candidate
            break

    parsed = _parse_date_range(date_raw)

    return {
        "title":       title,
        "company":     company,
        "dates":       date_raw,
        "start":       parsed["start"],
        "end":         parsed["end"],
        "duration":    parsed["duration"],
        "location":    location,
        "description": desc,
    }


def _scrape_experience(driver) -> list:
    """
    Extract the experience section. Handles both simple entries (one role)
    and grouped entries (multiple roles at the same company).

    LinkedIn's CSS selector for experience items matches items at ALL nesting
    levels, so we skip any item that has an ancestor <li> — those are nested
    role entries that will be handled when their parent company item is processed.
    """
    experience = []
    try:
        items = driver.find_elements(
            By.CSS_SELECTOR, "#experience ~ div .pvs-list__item--line-separated"
        )
        for item in items[:20]:
            # Skip nested items — they are inside a grouped company entry and will
            # be processed when we iterate over that parent item's sub-list.
            try:
                item.find_element(By.XPATH, "./ancestor::li[contains(@class,'pvs-list__item')]")
                continue
            except Exception:
                pass  # No ancestor li → this is a top-level item

            # Detect grouped entry: contains a nested <ul> with role sub-items
            nested_roles = item.find_elements(
                By.CSS_SELECTOR, "ul.pvs-list li.pvs-list__item--line-separated"
            )

            if nested_roles:
                # Top-level bold = company name; each nested li = one role
                top_bold = item.find_elements(
                    By.CSS_SELECTOR, "> div > div > div span.mr1.t-bold span[aria-hidden='true']"
                )
                company = top_bold[0].text.strip() if top_bold else ""

                for role_item in nested_roles[:8]:
                    entry = _extract_role(role_item)
                    if not entry["company"]:
                        entry["company"] = company
                    if entry["title"]:
                        experience.append(entry)
            else:
                entry = _extract_role(item)
                if entry["title"] or entry["company"]:
                    experience.append(entry)

    except Exception:
        pass

    return experience


def _scrape_education(driver) -> list:
    """Extract the education section with start/end/duration."""
    education = []
    try:
        items = driver.find_elements(
            By.CSS_SELECTOR, "#education ~ div .pvs-list__item--line-separated"
        )
        for item in items[:6]:
            bold   = item.find_elements(By.CSS_SELECTOR, "span.mr1.t-bold span[aria-hidden='true']")
            normal = item.find_elements(By.CSS_SELECTOR, "span.t-14.t-normal span[aria-hidden='true']")
            light  = item.find_elements(By.CSS_SELECTOR, "span.t-14.t-normal.t-black--light span[aria-hidden='true']")

            school   = bold[0].text.strip()   if bold   else ""
            degree   = normal[0].text.strip() if normal else ""
            date_raw = light[0].text.strip()  if light  else ""

            if school:
                parsed = _parse_date_range(date_raw)
                education.append({
                    "school":   school,
                    "degree":   degree,
                    "dates":    date_raw,
                    "start":    parsed["start"],
                    "end":      parsed["end"],
                    "duration": parsed["duration"],
                })
    except Exception:
        pass
    return education


def _scrape_posts(driver, profile_url: str) -> list:
    """Navigate to the recent-activity page and return up to 5 original posts."""
    base_url = profile_url.rstrip("/").split("?")[0]
    driver.get(f"{base_url}/recent-activity/all/")
    time.sleep(3)

    driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
    time.sleep(2)

    posts = []
    try:
        containers = driver.find_elements(By.CSS_SELECTOR, "div.feed-shared-update-v2")

        for container in containers[:15]:
            if len(posts) >= 5:
                break

            # Post text
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

            # Date — prefer the <time datetime="..."> absolute ISO date
            date_iso  = ""
            date_text = ""
            try:
                time_el  = container.find_element(By.CSS_SELECTOR, "time")
                date_iso  = time_el.get_attribute("datetime") or ""
                date_text = time_el.text.strip()
            except Exception:
                pass

            # Fall back to visible relative-date spans ("3w", "2mo", etc.)
            if not date_text:
                for sel in [
                    ".feed-shared-actor__sub-description span[aria-hidden='true']",
                    ".update-components-actor__sub-description span[aria-hidden='true']",
                ]:
                    try:
                        els = container.find_elements(By.CSS_SELECTOR, sel)
                        if els:
                            date_text = els[0].text.strip()
                            if date_text:
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

            entry = {"text": text, "date": date_text, "likes": likes}
            if date_iso:
                entry["date_iso"] = date_iso
            posts.append(entry)
    except Exception:
        pass

    return posts


def _build_timeline(experience: list, education: list, posts: list) -> list:
    """
    Flatten all dated career events into a single ordered list for the AI.
    LinkedIn returns experience newest-first, education newest-first, and
    posts newest-first, so we interleave them in that order.
    """
    events = []

    for exp in experience:
        period = ""
        if exp.get("start"):
            end  = exp.get("end") or "Present"
            dur  = f" ({exp['duration']})" if exp.get("duration") else ""
            period = f"{exp['start']} → {end}{dur}"

        events.append({
            "type":        "experience",
            "title":       exp.get("title", ""),
            "company":     exp.get("company", ""),
            "period":      period,
            "location":    exp.get("location", ""),
            "description": exp.get("description", ""),
        })

    for edu in education:
        period = ""
        if edu.get("start"):
            end = edu.get("end", "")
            dur = f" ({edu['duration']})" if edu.get("duration") else ""
            period = f"{edu['start']} → {end}{dur}".rstrip(" →")

        events.append({
            "type":    "education",
            "school":  edu.get("school", ""),
            "degree":  edu.get("degree", ""),
            "period":  period,
        })

    for post in posts:
        date = post.get("date_iso") or post.get("date", "")
        events.append({
            "type":  "post",
            "date":  date,
            "likes": post.get("likes", ""),
            "text":  post.get("text", "")[:300],
        })

    return events


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

    # ── Experience, education, skills, posts ───────────────────────────────
    experience = _scrape_experience(driver)
    education  = _scrape_education(driver)

    skills = []
    try:
        skill_els = driver.find_elements(
            By.CSS_SELECTOR, "#skills ~ div .mr1.t-bold span[aria-hidden='true']"
        )
        skills = [el.text.strip() for el in skill_els[:15] if el.text.strip()]
    except Exception:
        pass

    posts    = _scrape_posts(driver, url)
    timeline = _build_timeline(experience, education, posts)

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
        "timeline":    timeline,
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
