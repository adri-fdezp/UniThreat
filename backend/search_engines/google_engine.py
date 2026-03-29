import time
from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.remote.webelement import WebElement
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class GoogleSearch:
    """
    Modular Search Engine for Google.
    Handles the complexities of Selenium automation, result waiting, and data extraction.
    """
    
    def __init__(self, headless: bool = True):
        """
        Initialize the Google Search engine.

        :param headless: If True, runs Chrome without a visible window. 
                         Set to False to manually solve CAPTCHAs if detected.
        """
        self.headless = headless
        self.engine_name = "Google"

    def _get_driver(self) -> webdriver.Chrome:
        """
        Configures and returns a Chrome WebDriver instance with specific 
        anti-detection flags to minimize the risk of being blocked by Google.
        """
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless")
        
        # Anti-detection and stability arguments
        # --no-sandbox: Required for some environments (like Docker)
        # --disable-blink-features=AutomationControlled: Hides Selenium identifier
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Random user-agent to mimic a real browser
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Automatically manages the ChromeDriver binary
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=chrome_options)

    def _extract_result_data(self, element: WebElement) -> Optional[Dict[str, str]]:
        """
        Parses a single search result element to extract title, URL, description, and image.
        """
        try:
            # Extract Title
            title = ""
            h3_tags = element.find_elements(By.TAG_NAME, "h3")
            if h3_tags:
                title = h3_tags[0].text
            
            # Extract URL
            link = ""
            a_tags = element.find_elements(By.TAG_NAME, "a")
            if a_tags:
                link = a_tags[0].get_attribute("href")
            
            # Extract Snippet (Description)
            snippet = ""
            # Expanded list of common classes for Google result snippets
            snippet_selectors = [".VwiC3b", ".st", ".aCOpRe", ".y355M", ".IsZvec", ".ITZIwc", "div[style*='-webkit-line-clamp']"]
            for sel in snippet_selectors:
                snippets = element.find_elements(By.CSS_SELECTOR, sel)
                if snippets:
                    snippet = snippets[0].text
                    if snippet: # If we found a non-empty string, break
                        break
            
            # Fallback: if no specific snippet found, try to use the text of the container minus title
            if not snippet and title:
                full_text = element.text
                if full_text:
                    snippet = full_text.replace(title, "").replace(link, "").strip()
                    # Truncate if it's too long (likely junk)
                    if len(snippet) > 300: 
                        snippet = snippet[:300] + "..."

            # Extract Thumbnail (Potential Profile Picture)
            image_url = ""
            try:
                img_elem = element.find_elements(By.TAG_NAME, "img")
                if img_elem:
                    src = img_elem[0].get_attribute("src")
                    # Filter out small favicons, data URIs (often placeholders), or generic icons
                    if src and "data:image" not in src and "favicon" not in src:
                        image_url = src
            except Exception:
                pass # Image extraction is best-effort

            if title and link and link.startswith("http"):
                return {
                    "title": title,
                    "url": link,
                    "description": snippet,
                    "image": image_url,
                    "source": self.engine_name
                }
        except Exception:
            return None
            
        return None

    def search(self, query: str) -> List[Dict[str, str]]:
        """
        Performs a Google search for the specified query.
        
        :param query: The search string (e.g., 'site:linkedin.com "John Doe"')
        :return: A list of dictionaries containing result details.
        """
        results = []
        driver = self._get_driver()
        
        try:
            # Navigate to Google with the search query
            url = f"https://www.google.com/search?q={query}&hl=en"
            driver.get(url)
            
            try:
                # Wait up to 120 seconds for results. 
                # Long timeout allows manual CAPTCHA solving if headless=False.
                WebDriverWait(driver, 120).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.g, #search"))
                )
                
                # Multiple scrolls to ensure we trigger as much lazy loading as possible
                for _ in range(3):
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(1.5) 
                
            except Exception:
                # If timeout occurs, return empty list (assumed blocked or no results)
                return []

            # Locate result containers using multiple common Google selectors
            elements = driver.find_elements(By.CSS_SELECTOR, "div.g, div.tF2Cxc, div.v7W49e")
            print(f"[DEBUG] Raw elements found for '{query}': {len(elements)}")
            
            for el in elements:
                data = self._extract_result_data(el)
                if data:
                    print(f"[DEBUG] Extracted: {data['title'][:30]}... | {data['url'][:30]}...")
                    results.append(data)

            return results

        finally:
            # Ensure the browser is always closed to free up resources
            driver.quit()