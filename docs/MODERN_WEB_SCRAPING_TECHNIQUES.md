# Modern Web Scraping Techniques with Playwright - AI Agent Implementation Guide

## Executive Summary

This document provides comprehensive guidance for AI agents implementing modern web scraping solutions using Playwright and anti-detection techniques. Based on the latest developments in web automation (2024), this guide emphasizes stealth, efficiency, and reliability while avoiding common pitfalls like opening excessive browser windows.

## Table of Contents
1. [Core Principles](#core-principles)
2. [Technology Stack Overview](#technology-stack-overview)
3. [Anti-Detection Strategies](#anti-detection-strategies)
4. [Implementation Guidelines](#implementation-guidelines)
5. [Code Examples](#code-examples)
6. [Common Pitfalls to Avoid](#common-pitfalls-to-avoid)

---

## Core Principles

### 1. Browser Management
- **NEVER** open multiple browser windows unnecessarily
- Use a single browser context with multiple pages when needed
- Implement proper browser lifecycle management (open → use → close)
- Always run in headless mode for production scraping

### 2. Stealth First Approach
- Assume all websites have bot detection
- Implement human-like behavior by default
- Use proper anti-fingerprinting techniques
- Rotate user agents, proxies, and browser profiles

### 3. Resource Efficiency
- Minimize browser instances
- Reuse browser contexts when possible
- Implement proper cleanup and garbage collection
- Use async/await for concurrent operations

---

## Technology Stack Overview

### Recommended Libraries

#### 1. **Humanization-Playwright**
Advanced library for simulating human-like browser interactions.

**Installation:**
```bash
pip install humanization-playwright
```

**Key Features:**
- Human-like mouse movements using cubic Bezier curves
- Variable typing speeds with natural pauses
- Stealth mode via Patchright integration
- Support for different click types

**Usage Example:**
```python
from humanization_playwright import Humanization, HumanizationConfig

async def scrape_with_humanization():
    config = HumanizationConfig(
        fast=False,
        humanize=True,
        characters_per_minute=400,
        stealth_mode=True
    )
    
    humanization = await Humanization.undetected_launch(
        "/path/to/user_data_dir", 
        config
    )
    
    # Navigate with human-like behavior
    await humanization.page.goto("https://example.com")
    
    # Type with human-like speed and patterns
    search_input = humanization.page.locator("input#search")
    await humanization.type_at(search_input, "search query")
    
    # Click with natural mouse movement
    button = humanization.page.locator("button#submit")
    await humanization.click_at(button)
    
    # Always close the browser
    await humanization.browser.close()
```

#### 2. **Crawlee Python**
Production-ready web scraping framework with built-in anti-detection.

**Installation:**
```bash
python -m pip install 'crawlee[all]'
playwright install
```

**Key Features:**
- Unified interface for HTTP and browser scraping
- Automatic parallel crawling with concurrency control
- Built-in proxy rotation
- Automatic retries and error handling
- State persistence during interruptions

**Implementation Example:**
```python
import asyncio
from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext

async def main():
    # Configure crawler with anti-detection settings
    crawler = PlaywrightCrawler(
        max_requests_per_crawl=10,
        headless=True,  # Always use headless in production
        browser_type='chromium',
        use_session_pool=True,
        session_pool_options={
            'max_pool_size': 1,  # Limit browser instances
            'session_rotation_count': 5
        }
    )
    
    @crawler.router.default_handler
    async def request_handler(context: PlaywrightCrawlingContext):
        # Extract data
        data = {
            'url': context.request.url,
            'title': await context.page.title(),
            'content': await context.page.content()
        }
        
        # Store data
        await context.push_data(data)
        
        # Enqueue more URLs if needed
        await context.enqueue_links(
            selector='a.next-page',
            max_count=5
        )
    
    # Run crawler
    await crawler.run(['https://example.com'])
    
    # Export data
    await crawler.export_data('output.json')

if __name__ == '__main__':
    asyncio.run(main())
```

#### 3. **Undetected-ChromeDriver Alternative for Playwright**
While undetected-chromedriver is for Selenium, similar principles apply to Playwright.

**Playwright Stealth Configuration:**
```python
from playwright.async_api import async_playwright
import random

async def create_stealth_browser():
    async with async_playwright() as p:
        # Launch with stealth arguments
        browser = await p.chromium.launch(
            headless=True,  # Always headless for production
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-accelerated-2d-canvas',
                '--disable-gpu',
                f'--user-agent={get_random_user_agent()}'
            ]
        )
        
        # Create context with additional stealth settings
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
            timezone_id='America/New_York',
            permissions=['geolocation'],
            geolocation={'latitude': 40.7128, 'longitude': -74.0060},
            color_scheme='light',
            extra_http_headers={
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            }
        )
        
        # Add stealth scripts to every page
        await context.add_init_script("""
            // Override navigator.webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Override navigator.plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // Override navigator.languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
            
            // Override chrome
            window.chrome = {
                runtime: {}
            };
            
            // Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)
        
        return browser, context

def get_random_user_agent():
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0'
    ]
    return random.choice(user_agents)
```

---

## Anti-Detection Strategies

### 1. Avoiding Honeypot Traps

**Detection Methods:**
```python
async def detect_honeypots(page):
    """Detect and avoid honeypot elements"""
    
    # Find all links and inputs
    elements = await page.query_selector_all('a, input, button')
    
    honeypots = []
    for element in elements:
        # Check if element is hidden
        is_visible = await element.is_visible()
        
        # Check CSS properties
        display = await element.evaluate('el => window.getComputedStyle(el).display')
        visibility = await element.evaluate('el => window.getComputedStyle(el).visibility')
        opacity = await element.evaluate('el => window.getComputedStyle(el).opacity')
        
        # Check position
        position = await element.evaluate('el => window.getComputedStyle(el).position')
        left = await element.evaluate('el => el.offsetLeft')
        top = await element.evaluate('el => el.offsetTop')
        
        # Detect honeypots
        if (not is_visible or 
            display == 'none' or 
            visibility == 'hidden' or 
            float(opacity) == 0 or
            (position == 'absolute' and (left < -9999 or top < -9999))):
            
            honeypots.append(element)
    
    return honeypots

async def safe_click(page, selector):
    """Click only visible, non-honeypot elements"""
    element = await page.query_selector(selector)
    if element:
        is_honeypot = await detect_honeypots(page)
        if element not in is_honeypot:
            await element.click()
```

### 2. Browser Fingerprinting Countermeasures

**Key Areas to Address:**
- Canvas fingerprinting
- WebGL fingerprinting
- Audio fingerprinting
- Font fingerprinting
- Screen resolution
- Timezone and language
- Hardware concurrency

**Implementation:**
```python
async def apply_anti_fingerprinting(context):
    """Apply comprehensive anti-fingerprinting measures"""
    
    await context.add_init_script("""
        // Canvas fingerprinting protection
        const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function(type) {
            if (type === 'image/png' && this.width === 280 && this.height === 60) {
                return 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==';
            }
            return originalToDataURL.apply(this, arguments);
        };
        
        // WebGL fingerprinting protection
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) {
                return 'Intel Inc.';
            }
            if (parameter === 37446) {
                return 'Intel Iris OpenGL Engine';
            }
            return getParameter.apply(this, arguments);
        };
        
        // Audio fingerprinting protection
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        if (AudioContext) {
            AudioContext.prototype.__proto__.getChannelData = new Proxy(
                AudioContext.prototype.__proto__.getChannelData,
                {
                    apply: function(target, thisArg, argumentsList) {
                        const result = target.apply(thisArg, argumentsList);
                        for (let i = 0; i < result.length; i += 100) {
                            result[i] = result[i] + 0.0000001;
                        }
                        return result;
                    }
                }
            );
        }
        
        // Randomize hardware concurrency
        Object.defineProperty(navigator, 'hardwareConcurrency', {
            get: () => 4 + Math.floor(Math.random() * 4)
        });
        
        // Randomize device memory
        Object.defineProperty(navigator, 'deviceMemory', {
            get: () => 8
        });
    """)
```

### 3. Request Pattern Humanization

**Implementation:**
```python
import asyncio
import random

class HumanBehaviorSimulator:
    """Simulate human-like browsing patterns"""
    
    @staticmethod
    async def random_delay(min_seconds=1, max_seconds=3):
        """Add random delays between actions"""
        delay = random.uniform(min_seconds, max_seconds)
        await asyncio.sleep(delay)
    
    @staticmethod
    async def simulate_reading(page, min_scroll=3, max_scroll=7):
        """Simulate reading behavior with scrolling"""
        scroll_count = random.randint(min_scroll, max_scroll)
        
        for _ in range(scroll_count):
            # Random scroll distance
            scroll_distance = random.randint(100, 500)
            await page.evaluate(f'window.scrollBy(0, {scroll_distance})')
            
            # Reading delay
            await HumanBehaviorSimulator.random_delay(0.5, 2)
    
    @staticmethod
    async def move_mouse_naturally(page):
        """Simulate natural mouse movements"""
        viewport = await page.viewport_size()
        if viewport:
            for _ in range(random.randint(2, 5)):
                x = random.randint(0, viewport['width'])
                y = random.randint(0, viewport['height'])
                await page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.1, 0.3))
    
    @staticmethod
    async def type_like_human(page, selector, text):
        """Type with human-like speed and patterns"""
        element = await page.query_selector(selector)
        if element:
            await element.click()
            
            for char in text:
                await element.type(char)
                # Variable typing speed
                if char == ' ':
                    await asyncio.sleep(random.uniform(0.1, 0.3))
                else:
                    await asyncio.sleep(random.uniform(0.05, 0.15))
                
                # Occasional longer pauses (thinking)
                if random.random() < 0.1:
                    await asyncio.sleep(random.uniform(0.5, 1.5))
```

---

## Implementation Guidelines

### 1. Single Browser Instance Pattern

**CRITICAL:** Never open multiple browser windows unnecessarily.

```python
class BrowserManager:
    """Manage a single browser instance efficiently"""
    
    def __init__(self):
        self.browser = None
        self.context = None
        self.pages = {}
    
    async def initialize(self):
        """Initialize single browser instance"""
        if not self.browser:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(
                headless=True,  # ALWAYS headless in production
                args=['--disable-blink-features=AutomationControlled']
            )
            self.context = await self.browser.new_context()
    
    async def get_page(self, page_id='default'):
        """Get or create a page within the single browser context"""
        if page_id not in self.pages:
            self.pages[page_id] = await self.context.new_page()
        return self.pages[page_id]
    
    async def close_page(self, page_id):
        """Close a specific page"""
        if page_id in self.pages:
            await self.pages[page_id].close()
            del self.pages[page_id]
    
    async def cleanup(self):
        """Clean up all resources"""
        for page in self.pages.values():
            await page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()

# Usage
async def scrape_multiple_sites():
    manager = BrowserManager()
    await manager.initialize()
    
    try:
        # Use single browser for multiple sites
        for site in ['site1.com', 'site2.com']:
            page = await manager.get_page('scraper')
            await page.goto(f'https://{site}')
            # Scrape data
            await manager.close_page('scraper')
    finally:
        await manager.cleanup()
```

### 2. Error Handling and Retry Logic

```python
class RobustScraper:
    """Implement robust scraping with proper error handling"""
    
    def __init__(self, max_retries=3):
        self.max_retries = max_retries
        self.browser_manager = BrowserManager()
    
    async def scrape_with_retry(self, url, scrape_function):
        """Scrape with automatic retry on failure"""
        for attempt in range(self.max_retries):
            try:
                await self.browser_manager.initialize()
                page = await self.browser_manager.get_page()
                
                # Navigate with timeout
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                
                # Execute scraping logic
                result = await scrape_function(page)
                
                return result
                
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {str(e)}")
                
                if attempt == self.max_retries - 1:
                    raise
                
                # Exponential backoff
                await asyncio.sleep(2 ** attempt)
                
                # Reset browser on failure
                await self.browser_manager.cleanup()
                self.browser_manager = BrowserManager()
        
        return None
```

### 3. Concurrent Scraping Without Multiple Browsers

```python
class ConcurrentScraper:
    """Scrape multiple URLs concurrently using a single browser"""
    
    def __init__(self, max_concurrent_pages=3):
        self.max_concurrent_pages = max_concurrent_pages
        self.semaphore = asyncio.Semaphore(max_concurrent_pages)
    
    async def scrape_url(self, context, url):
        """Scrape a single URL with concurrency control"""
        async with self.semaphore:
            page = await context.new_page()
            try:
                await page.goto(url)
                # Scraping logic here
                data = await page.title()
                return {'url': url, 'title': data}
            finally:
                await page.close()
    
    async def scrape_all(self, urls):
        """Scrape multiple URLs concurrently"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            
            try:
                tasks = [self.scrape_url(context, url) for url in urls]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                return [r for r in results if not isinstance(r, Exception)]
            finally:
                await browser.close()
```

---

## Common Pitfalls to Avoid

### 1. **Opening Multiple Browser Windows**
**Problem:** Opening hundreds of browser windows
**Solution:** Use a single browser with multiple pages or tabs

### 2. **Not Running Headless**
**Problem:** Visible browser windows popping up
**Solution:** Always use `headless=True` in production

### 3. **Ignoring Rate Limiting**
**Problem:** Getting blocked due to too many requests
**Solution:** Implement delays and respect robots.txt

### 4. **Poor Resource Management**
**Problem:** Memory leaks from unclosed browsers
**Solution:** Always use try/finally or context managers

### 5. **Detectable Automation Patterns**
**Problem:** Consistent timing, no mouse movement
**Solution:** Add randomization and human-like behavior

### 6. **Ignoring JavaScript Rendering**
**Problem:** Missing dynamic content
**Solution:** Wait for content to load properly

```python
# Wait strategies
await page.wait_for_selector('.dynamic-content', timeout=10000)
await page.wait_for_load_state('networkidle')
await page.wait_for_function('() => document.querySelector(".content").innerText.length > 0')
```

---

## Production-Ready Implementation Template

```python
"""
Production-ready web scraper with all best practices
"""

import asyncio
import logging
from typing import List, Dict, Optional
from playwright.async_api import async_playwright, Page
import random

class ProductionScraper:
    """Production-ready scraper with anti-detection and efficiency"""
    
    def __init__(self, 
                 headless: bool = True,
                 max_concurrent: int = 3,
                 use_proxy: bool = False,
                 proxy_list: Optional[List[str]] = None):
        self.headless = headless
        self.max_concurrent = max_concurrent
        self.use_proxy = use_proxy
        self.proxy_list = proxy_list or []
        self.logger = logging.getLogger(__name__)
        
    async def create_stealth_context(self, browser):
        """Create a browser context with stealth settings"""
        context_options = {
            'viewport': {'width': 1920, 'height': 1080},
            'user_agent': self._get_random_user_agent(),
            'locale': 'en-US',
            'timezone_id': 'America/New_York',
        }
        
        if self.use_proxy and self.proxy_list:
            proxy = random.choice(self.proxy_list)
            context_options['proxy'] = {'server': proxy}
        
        context = await browser.new_context(**context_options)
        
        # Add stealth scripts
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        return context
    
    def _get_random_user_agent(self) -> str:
        """Get random user agent"""
        agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        ]
        return random.choice(agents)
    
    async def scrape_single(self, page: Page, url: str) -> Dict:
        """Scrape a single URL"""
        try:
            # Add random delay
            await asyncio.sleep(random.uniform(1, 3))
            
            # Navigate
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            
            # Simulate human behavior
            await self._simulate_human_behavior(page)
            
            # Extract data (customize this)
            title = await page.title()
            
            return {
                'url': url,
                'title': title,
                'success': True
            }
            
        except Exception as e:
            self.logger.error(f"Error scraping {url}: {str(e)}")
            return {
                'url': url,
                'error': str(e),
                'success': False
            }
    
    async def _simulate_human_behavior(self, page: Page):
        """Simulate human-like behavior"""
        # Random scroll
        for _ in range(random.randint(1, 3)):
            await page.evaluate(f'window.scrollBy(0, {random.randint(100, 300)})')
            await asyncio.sleep(random.uniform(0.5, 1.5))
    
    async def scrape_urls(self, urls: List[str]) -> List[Dict]:
        """Scrape multiple URLs efficiently"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.headless,
                args=['--disable-blink-features=AutomationControlled']
            )
            
            context = await self.create_stealth_context(browser)
            
            try:
                # Create semaphore for concurrency control
                semaphore = asyncio.Semaphore(self.max_concurrent)
                
                async def scrape_with_semaphore(url):
                    async with semaphore:
                        page = await context.new_page()
                        try:
                            return await self.scrape_single(page, url)
                        finally:
                            await page.close()
                
                # Scrape all URLs concurrently
                tasks = [scrape_with_semaphore(url) for url in urls]
                results = await asyncio.gather(*tasks)
                
                return results
                
            finally:
                await browser.close()

# Usage example
async def main():
    scraper = ProductionScraper(
        headless=True,  # ALWAYS True in production
        max_concurrent=3,  # Limit concurrent pages
        use_proxy=False  # Enable if needed
    )
    
    urls = [
        'https://example1.com',
        'https://example2.com',
        'https://example3.com'
    ]
    
    results = await scraper.scrape_urls(urls)
    print(f"Scraped {len(results)} URLs")
    
    # Process results
    successful = [r for r in results if r['success']]
    print(f"Success rate: {len(successful)}/{len(results)}")

if __name__ == '__main__':
    asyncio.run(main())
```

---

## Summary and Best Practices Checklist

### ✅ Always Do:
- [ ] Run browsers in headless mode for production
- [ ] Use a single browser instance with multiple pages
- [ ] Implement proper error handling and retries
- [ ] Add random delays between actions
- [ ] Rotate user agents and headers
- [ ] Clean up resources properly
- [ ] Implement anti-fingerprinting measures
- [ ] Respect robots.txt and rate limits
- [ ] Use async/await for efficiency
- [ ] Log errors and monitor performance

### ❌ Never Do:
- [ ] Open multiple browser windows unnecessarily
- [ ] Run with `headless=False` in production
- [ ] Make requests without delays
- [ ] Ignore error handling
- [ ] Leave browsers/pages open after use
- [ ] Use default browser fingerprints
- [ ] Scrape without checking robots.txt
- [ ] Click on hidden/honeypot elements
- [ ] Use predictable patterns
- [ ] Ignore memory management

---

## Additional Resources

- Playwright Documentation: https://playwright.dev/python/
- Browser Automation Best Practices: https://www.scraperapi.com/blog/web-scraping-best-practices/
- Anti-Bot Evasion Techniques: Regular updates needed as detection evolves

## Version History
- v1.0 (2024): Initial comprehensive guide based on latest scraping techniques

---

**Note for AI Agents:** This guide represents current best practices as of 2024. Always verify the latest versions of libraries and adjust techniques based on the specific requirements of each scraping task. The key principle remains: minimize detection while maximizing efficiency and reliability.
ntroduction
Cloudflare is a leading web protection service, widely used to block bots and scrapers through sophisticated browser fingerprinting, JavaScript challenges, and CAPTCHAs. These defenses can stop most traditional scrapers cold. However, with Playwright, a modern browser automation tool, you can emulate real users more convincingly and bypass many of Cloudflare's layers. In this guide, you’ll learn how to build a resilient scraping setup using Playwright, stealth plugins, proxies, and human-like behavior to access data from Cloudflare-protected websites.

How Cloudflare Blocks Scrapers
Cloudflare uses a layered system to detect and block scrapers. Most of these defenses are invisible to regular users but are designed to catch any sign of automation. To get around them, it’s not enough to use a headless browser; you need to understand how these systems work and what they’re looking for.

The first layer involves JavaScript and browser checks. When a page loads, Cloudflare runs scripts that look for expected browser behaviors, such as how the browser renders content, how quickly it executes JS, and whether specific properties exist in the window.navigator. Tools like Playwright can run JavaScript, but using it in a default configuration often leaves signs that a real user isn’t present. That’s usually enough to trigger a block.

Then there’s TLS and JA3 fingerprinting. Every browser has a specific way it initiates secure connections, and Cloudflare captures that fingerprint during the TLS handshake. Scrapers that use different TLS configurations, especially those that don’t match popular browsers, stand out. Even if the script looks like it’s coming from Chrome, the TLS fingerprint might say otherwise.

CAPTCHAs are another defense mechanism, not just for login forms. Cloudflare can serve hCaptcha or Turnstile challenges whenever it detects something suspicious, like repeated access from the same IP, strange headers, or automation signatures. These challenges can stop your scraper completely unless you detect and solve them dynamically.

Cloudflare looks at IP reputation and request pattern, and your IP might get flagged if it is part of a known proxy pool or has made too many rapid requests. Even a small spike in traffic can result in throttling or temporary bans. Changing IPs, managing session cookies, and pacing your requests are all necessary if you want to keep access over time.

To overcome these defenses, your scraper needs to behave like a real browser and a real user. That means mimicking everything from connection-level details to UI behavior without cutting corners.

Setting Up Playwright with Stealth Mode
Playwright gives you direct access to real browser instances, Chromium, Firefox, and WebKit, all of which support full JavaScript execution and page rendering.

But to get past Cloudflare reliably, a standard browser session isn’t enough. You’ll need to take extra steps to hide signs of automation.

That’s where playwright-extra and stealth plugins help these tools modify browser characteristics that Cloudflare often checks, such as navigator.webdriver, missing WebGL features, or the presence of headless-specific headers.

To get started, install the required packages in your Node.js project:

npm install playwright-extra playwright-extra-plugin-stealth
Copy
Then, create a custom Playwright instance that uses the stealth plugin:

// Playwright-extra allows plugin support — needed for stealth
const { chromium } = require('playwright-extra');

// Load the stealth plugin and use defaults (all tricks to hide playwright usage)
// Note: playwright-extra is compatible with most puppeteer-extra plugins
const stealth = require('puppeteer-extra-plugin-stealth')()

// Important: this step must happen BEFORE launching the browser
chromium.use(stealth); // Without this, Cloudflare will likely detect automation and serve a challenge
Copy
Once that’s set up, you can randomize elements of your browser fingerprint. Viewport dimensions, user-agent strings, language headers, and timezone values contribute to whether the session looks human or automated. These small details matter because Cloudflare’s detection looks at inconsistencies across multiple signals.

const browser = await chromium.launch({ headless: false }); // Headed mode reduces detection; avoid headless=true if possible

const context = await browser.newContext({
  // Real users don’t have consistent viewports — this helps avoid fingerprint mismatches
  viewport: {
    width: 1280 + Math.floor(Math.random() * 100), // Randomize a bit
    height: 720 + Math.floor(Math.random() * 100)
  },
  userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)...', // Use a real user-agent, ideally from your proxy location
  locale: 'en-US',                    // Match browser locale to IP region
  timezoneId: 'America/New_York',     // Timezone mismatches are a red flag in Cloudflare fingerprinting
});
Copy
Sessions should be persistent, reusing cookies and local storage data across requests helps make your scraper less suspicious. You can save and load the browser context from disk instead of starting from a clean slate every time.

const userDataDir = './session-profile'; // This folder stores cookies, localStorage, etc.

const browser = await chromium.launchPersistentContext(userDataDir, {
  headless: false, // Again, headed = more human-like
  args: ['--start-maximized'] // Optional, but full-screen windows mimic real usage
});

// Use this approach if the site expects you to "stay logged in" or keep a shopping cart session
// Note: Too many local sessions can get messy, rotate or clean up as needed
Copy
With this setup, your Playwright sessions behave more like real browser activity and less like automation. That gives you a better chance of bypassing Cloudflare without being blocked on the first request.

Rotating Proxies and Handling CAPTCHA Challenges
Cloudflare watches traffic patterns across IP addresses. If an IP sends too many requests, triggers multiple challenges, or matches known bad behavior, it can be throttled or blocked entirely.

To reduce the chances of that happening, you can rotate through residential or datacenter proxies using the --proxy-server flag in Playwright. This gives each session a different IP, which helps distribute your request volume and avoid detection.

Here’s how to launch a Playwright browser with a proxy:

onst browser = await chromium.launch({
  headless: false,
  args: [
    // Always use authenticated proxies, preferably residential/mobile
    '--proxy-server=http://username:password@proxy-ip:port' // Format: scheme://user:pass@host:port
  ]
});

const page = await browser.newPage(); // Proxy is applied to this page and all further requests

// Caveat: Avoid using the same proxy too frequently, or you’ll get rate-limited or banned
Copy
Cloudflare might still challenge the request with a CAPTCHA even with a fresh IP. When that happens, your scraper must detect and solve it or skip the page. One way to do that is by checking for an iframe that loads a CAPTCHA, like this:

// Check if Cloudflare is presenting a CAPTCHA challenge
const isCaptchaPresent = await page.$('iframe[src*="captcha"]');

if (isCaptchaPresent) {
  console.log('CAPTCHA detected – will need to solve or switch proxy');
}

// Important: Cloudflare can serve invisible challenges too, always monitor response timing and errors, not just DOM
Copy
For sites using hCaptcha or reCAPTCHA, third-party services like 2Captcha or CapMonster can solve challenges programmatically. These services take a sitekey and page URL, return a token, and then you inject that token into the form. Some tools (like @extra/recaptcha) simplify this by automating the full solve step:

const RecaptchaPlugin = require('@extra/recaptcha');

// Register plugin to handle reCAPTCHA/hCaptcha solving via 2Captcha
chromium.use(
  RecaptchaPlugin({
    provider: {
      id: '2captcha',
      token: 'YOUR_2CAPTCHA_API_KEY' // Note: This burns credits every time; don’t solve CAPTCHAs unnecessarily
    },
    visualFeedback: true // Shows animations like checkbox checking (great for debugging)
  })
);

// This solves any visible captchas on the current page — usually required on Cloudflare-protected forms
await page.solveRecaptchas();

// Caveat: If CAPTCHA fails, you’ll need to rotate proxy or log the error
Copy
Once the CAPTCHA is handled or skipped, you can proceed with your scrape as normal. To prevent the CAPTCHA from appearing again on the next visit, save cookies and session storage data after a successful scrape. This creates continuity between visits and helps the session look more human.

// After a successful login or scrape, save the cookies
const cookies = await context.cookies();
fs.writeFileSync('./cookies.json', JSON.stringify(cookies, null, 2)); // Save to disk

// On future runs, restore session to avoid challenges/login
const savedCookies = JSON.parse(fs.readFileSync('./cookies.json'));
await context.addCookies(savedCookies);

// This makes your scraper look like it's just a returning user huge advantage on Cloudflare or login-gated sites
Copy
Rotating proxies, solving CAPTCHAs, and maintaining session state work together to help you get through Cloudflare’s layers without interruption. Scrapers that skip these steps usually don’t last more than a few requests.

Scraping After Cloudflare with Playwright
Once you've configured stealth mode and rotated proxies, you can move on to an actual scraping flow. This part combines everything: proxy setup, fingerprint masking, challenge detection, and data extraction. You're not just testing if the page loads; you’re trying to access real content without getting flagged midway through the session.

To start, launch Playwright with your proxy configured. Ensure it’s a working residential or datacenter proxy with low block rates. Then, set a real user-agent string to replace the default one, which is often tied to automation.

// Launch the browser with a proxy assigned
const browser = await chromium.launch({
  headless: false, // Run in full (headed) mode — helps bypass basic bot checks
  args: [
    `--proxy-server=${proxy}` // Proxy format: http://username:password@ip:port
  ]
});

// Create a fresh context (new browser profile, isolated cookies, etc.)
const context = await browser.newContext();
const page = await context.newPage();

// Set a realistic User-Agent string to avoid detection
await page.setUserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36");
// Caveats:
// - Avoid reusing the same proxy & UA combo too often
// - Cloudflare may still fingerprint you on TLS/JA3 signature rotating IP alone won’t always help
Copy
Once the browser is ready, load the target page for Cloudflare-protected sites. It’s better to wait a few extra seconds to let JavaScript challenges pass quietly in the background. These challenges don’t always show visual feedback, so that that timing can matter.

await page.goto("https://target-cloudflare-site.com", { waitUntil: "domcontentloaded" });
await page.waitForTimeout(5000); // gives Cloudflare a chance to finish background checks
Copy
Check if a CAPTCHA exists; you can detect this by searching for known patterns in iframes or specific HTML containers. If it’s present, you can call your CAPTCHA handler, retry with a different proxy, or mark the proxy as burned.

// Attempt to detect if CAPTCHA is present before scraping
const captchaPresent = await page.$('iframe[src*="captcha"]');

if (captchaPresent) {
  console.log("CAPTCHA detected");
  // Either solve, switch to another proxy, or delay the request
  // Pro tip: mark this proxy as "burned" in a proxy pool so you don’t reuse it too soon
} else {
  const content = await page.evaluate(() => document.body.innerText); // Grab visible content
  console.log("Scraped content:", content);
}
Copy
Once the content is accessible, store session cookies and scrape the needed data. You’ve cleared the challenge and landed on the real page. From here, your scraper can move forward confidently, pull the data, close the session cleanly, or continue cycling through the next URL with a new proxy.

This pattern works well for batches of URLs, especially if you’re tracking proxy performance and retrying only the ones that hit a CAPTCHA or fail the JS checks. It’s repeatable and flexible without relying on third-party scraping tools.

Using BQL to Handle Stubborn Cloudflare Pages
Sometimes, even a well-configured Playwright setup doesn’t cut through Cloudflare. You’ve got stealth, proxies, and CAPTCHA solvers, all wired up, but the site still detects automation and either blocks access or keeps you stuck in a challenge loop.

When that happens consistently, offloading the scraping to a headless browser-as-a-service like Browserless, specifically using BQL (Browserless Query Language), is often the most reliable path forward.

Cloudflare CAPTCHAs are one of the biggest pain points in browser automation, especially when sites Cloudflare serves them in iframes, shadow DOMs, or in response to unusual behavior.

With Playwright, you’d usually need to detect the CAPTCHA manually, integrate with a solver like 2Captcha, inject tokens, and cross your fingers.

Browserless simplifies all of that with two built-in mutations:

verify: For Cloudflare's "Are you human?" checks (the simple click-to-proceed pages).
solve: For full hCaptcha and reCAPTCHA challenges.
Example 1: Bypass Cloudflare’s “Human Check”
mutation VerifyChallenge {
  goto(url: "https://protected.domain") {
    status
  }

  verify(type: cloudflare) {
    found    # true if a challenge was detected
    solved   # true if it was auto-handled
    time     # how long it took in ms
  }
}
Copy
This works for the common Cloudflare interstitials that just want a human presence, no CAPTCHA solving involved. If found, BQL clicks the verify button for you.

Example 2: Solve hCaptcha or reCAPTCHA Automatically
mutation SolveCaptcha {
  goto(url: "https://protected.domain") {
    status
  }

  solve(type: hcaptcha) {
    found
    solved
    time
  }
}
Copy
BQL detects the CAPTCHA, finds the form, solves it, and returns structured feedback without installing third-party solvers or APIs.

Conclusion
Cloudflare makes scraping harder than ever, especially with new challenges like Turnstile, stronger fingerprinting, and aggressive rate-limiting. Playwright still gives you a powerful edge, especially when combined with stealth plugins, solid proxy hygiene, and session-aware automation. But it's worth leveling up if you’re hitting limits with local scripts or dealing with constant maintenance to keep things working. Browserless with BQL is built for these kinds of scraping jobs. It handles the stealth, scale, and infrastructure so you can focus on getting the data you need. Start using BQL and spend less time solving CAPTCHAs, more time shipping scrapers that actually work.

FAQs
Can Playwright bypass Cloudflare Turnstile and hCaptcha in 2025?
Yes, Playwright can sometimes bypass both Cloudflare Turnstile and hCaptcha, but it’s not something that works out of the box. These increasingly sophisticated challenges require more than running a headless browser. You’ll need to integrate third-party CAPTCHA-solving services like 2Captcha or CapMonster, detect the presence of CAPTCHAs on the page using selectors (such as iframe containers for Turnstile or hCaptcha), and solve them programmatically before continuing with scraping. Using playwright-extra with stealth plugins helps reduce the chances of being flagged before the challenge even appears. Pairing that with persistent browser sessions and cookies can help reduce how often CAPTCHAs are triggered across multiple requests.

Why does Cloudflare still block Playwright even with stealth mode enabled?
Playwright can still get blocked even with stealth mode enabled because Cloudflare looks far beyond simple browser signals. While stealth plugins help mask things like navigator.webdriver and common headless indicators, they don’t cover deeper-level fingerprinting. Cloudflare analyzes TLS signatures (like JA3), HTTP/2 frame order, and browser consistency, for example, to determine whether your timezone, language, and IP region align. It raises suspicion if your proxy is in one country but your browser fingerprint says you're in another. Randomizing viewport, fonts, geolocation, and language headers is helpful, but sometimes it’s not enough without matching all fingerprint layers.

What’s the best proxy setup for scraping Cloudflare-protected websites with Playwright?
The most effective proxy setup for scraping Cloudflare-protected sites with Playwright involves using rotating residential or mobile proxies that support authentication. Datacenter proxies tend to get flagged quickly, especially if shared across users. For Playwright, proxies can be passed via the --proxy-server launch argument. It’s also important to keep your browser profile consistent with the proxy things like language headers, timezone, and user agent, which should all align with the IP's country and region. If your target site uses geo-based filtering or fingerprinting, matching these values can help reduce the chance of being challenged.

When should you switch from Playwright to Browserless or BQL for Cloudflare scraping?
If you’re running into repeated blocks, solving CAPTCHAs manually, or struggling to scale scraping across multiple pages or sessions, switching to Browserless or BQL is probably time. These are cloud-native solutions designed for scraping at scale, with built-in support for stealth, proxy rotation, session management, and CAPTCHA solving. You don’t have to manage browser instances or infrastructure manually. BQL (Browserless Query Language) simplifies scraping by allowing you to define scrape logic declaratively through an API. It’s especially useful when scraping thousands of pages concurrently or maintaining stable, long-running scraping jobs without micromanaging every browser interaction.