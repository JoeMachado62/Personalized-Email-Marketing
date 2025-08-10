"""
Direct test of Selenium to ensure it works
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

# Setup Chrome
options = webdriver.ChromeOptions()
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)

# Create driver
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

try:
    # Search for Broadway Auto Brokers
    query = "BROADWAY AUTO BROKERS INC ALACHUA FL"
    url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    
    print(f"Navigating to: {url}")
    driver.get(url)
    
    # Wait for page to load
    time.sleep(3)
    
    # Find all divs that might contain results
    results = driver.find_elements(By.CSS_SELECTOR, "div.g")
    print(f"Found {len(results)} div.g elements")
    
    if not results:
        # Try alternative selector
        results = driver.find_elements(By.XPATH, "//div[.//h3]")
        print(f"Found {len(results)} divs with h3")
    
    # Extract data
    found_results = []
    for result in results[:5]:
        try:
            title = result.find_element(By.TAG_NAME, "h3").text
            link = result.find_element(By.TAG_NAME, "a").get_attribute("href")
            print(f"\nTitle: {title}")
            print(f"URL: {link}")
            found_results.append({"title": title, "url": link})
        except:
            pass
    
    print(f"\n\nTotal extracted: {len(found_results)} results")
    
    # Keep browser open for 5 seconds to see results
    time.sleep(5)
    
finally:
    driver.quit()
    print("Browser closed")