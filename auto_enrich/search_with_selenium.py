"""
Search using Selenium with a real Chrome browser - exactly like a human would.
This avoids all bot detection issues.
"""

import time
import logging
from typing import List, Dict, Any
from urllib.parse import quote_plus
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger(__name__)


class RealChromeSearch:
    """Use Selenium with real Chrome to search exactly like a human"""
    
    def __init__(self, headless: bool = False):
        """
        Initialize Chrome browser.
        
        Args:
            headless: If True, run in headless mode. False for visible browser.
        """
        self.headless = headless
        self.driver = None
    
    def start_browser(self):
        """Start Chrome browser with human-like settings"""
        options = Options()
        
        # Make it look like a real browser
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Use a real user profile (optional)
        # options.add_argument(r"user-data-dir=C:\Users\joema\AppData\Local\Google\Chrome\User Data")
        
        if self.headless:
            options.add_argument("--headless=new")  # New headless mode
        
        # Window size
        options.add_argument("--window-size=1920,1080")
        
        # Initialize driver with automatic driver management
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        
        # Remove webdriver property
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        logger.info("Chrome browser started successfully")
    
    def search_google(self, query: str) -> List[Dict[str, Any]]:
        """
        Search Google and extract results.
        
        Args:
            query: Search query string
            
        Returns:
            List of search results with title, url, snippet
        """
        if not self.driver:
            self.start_browser()
        
        results = []
        
        try:
            # Navigate to Google
            search_url = f"https://www.google.com/search?q={quote_plus(query)}"
            logger.info(f"Searching Google for: {query}")
            self.driver.get(search_url)
            
            # Wait for results to load
            wait = WebDriverWait(self.driver, 10)
            
            # Wait a bit for page to fully load
            time.sleep(2)
            
            # Use XPath to find results - most reliable across Google's changing HTML
            search_results = self.driver.find_elements(By.XPATH, "//div[.//h3]")
            logger.info(f"Found {len(search_results)} potential result divs")
            
            # If that's too many, try to be more specific
            if len(search_results) > 50:
                # Try standard result containers
                specific_results = self.driver.find_elements(By.CSS_SELECTOR, "div.g")
                if specific_results:
                    search_results = specific_results
                    logger.info(f"Using div.g selector: {len(search_results)} results")
                else:
                    # Limit to reasonable number
                    search_results = search_results[:20]
                    logger.info(f"Limited to first 20 results")
            
            # Extract data from results
            for result in search_results[:10]:  # Get top 10 results
                try:
                    # Try to find title (h3 element)
                    title_elem = result.find_element(By.TAG_NAME, "h3")
                    title = title_elem.text if title_elem else ""
                    
                    # Try to find link
                    link_elem = result.find_element(By.TAG_NAME, "a")
                    url = link_elem.get_attribute("href") if link_elem else ""
                    
                    # Try to find snippet
                    snippet = ""
                    try:
                        # Try multiple snippet selectors
                        for snippet_selector in ["span.aCOpRe", "div.VwiC3b", "div.IsZvec", "span"]:
                            snippet_elems = result.find_elements(By.CSS_SELECTOR, snippet_selector)
                            if snippet_elems:
                                snippet = snippet_elems[0].text
                                break
                    except:
                        pass
                    
                    # Only add if we have meaningful data
                    if title and url and not url.startswith("https://www.google.com"):
                        results.append({
                            "title": title,
                            "url": url,
                            "snippet": snippet[:200] if snippet else "",
                            "source": "google_selenium"
                        })
                        logger.debug(f"Found result: {title[:50]}...")
                        
                except Exception as e:
                    logger.debug(f"Error extracting result: {e}")
                    continue
            
            # Also check for Google My Business panel
            try:
                gmb_panel = self.driver.find_element(By.CSS_SELECTOR, "div[data-attrid*='kc:/local']")
                if gmb_panel:
                    # Extract business info
                    business_name = ""
                    website = ""
                    phone = ""
                    
                    try:
                        name_elem = gmb_panel.find_element(By.CSS_SELECTOR, "h2[data-attrid='title']")
                        business_name = name_elem.text
                    except:
                        pass
                    
                    try:
                        website_elem = gmb_panel.find_element(By.CSS_SELECTOR, "a[data-attrid*='website']")
                        website = website_elem.get_attribute("href")
                    except:
                        pass
                    
                    try:
                        phone_elem = gmb_panel.find_element(By.CSS_SELECTOR, "span[data-attrid*='phone']")
                        phone = phone_elem.text
                    except:
                        pass
                    
                    if business_name:
                        gmb_result = {
                            "title": business_name,
                            "url": website or f"https://www.google.com/search?q={quote_plus(business_name)}",
                            "snippet": f"Google My Business listing. Phone: {phone}" if phone else "Google My Business listing",
                            "source": "google_my_business",
                            "phone": phone,
                            "is_gmb": True
                        }
                        results.insert(0, gmb_result)  # Put GMB result first
                        logger.info(f"Found Google My Business panel for: {business_name}")
            except:
                pass
            
            logger.info(f"Google search completed: {len(results)} results found")
            
        except Exception as e:
            logger.error(f"Google search error: {str(e)}")
        
        return results
    
    def close(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            logger.info("Browser closed")
    
    def __enter__(self):
        """Context manager entry"""
        self.start_browser()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


def search_with_real_chrome(query: str, headless: bool = False) -> List[Dict[str, Any]]:
    """
    Convenience function to search with real Chrome.
    
    Args:
        query: Search query
        headless: Run in headless mode
        
    Returns:
        List of search results
    """
    with RealChromeSearch(headless=headless) as searcher:
        return searcher.search_google(query)


if __name__ == "__main__":
    # Test the search
    logging.basicConfig(level=logging.INFO)
    
    test_query = "BROADWAY AUTO BROKERS INC ALACHUA FL"
    print(f"Testing search for: {test_query}")
    
    results = search_with_real_chrome(test_query, headless=False)
    
    print(f"\nFound {len(results)} results:")
    for i, result in enumerate(results[:5], 1):
        print(f"\n{i}. {result['title']}")
        print(f"   URL: {result['url']}")
        print(f"   Snippet: {result['snippet'][:100]}...")