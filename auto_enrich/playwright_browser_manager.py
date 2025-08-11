"""
Playwright Browser Manager with Anti-Detection and Stealth Features
Singleton pattern ensures only ONE browser instance is ever created.
"""

import asyncio
import sys
import random
import logging
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright

# Fix Windows event loop for Playwright compatibility
if sys.platform == 'win32':
    # Windows REQUIRES ProactorEventLoop for subprocess support
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except:
        pass  # May already be set

logger = logging.getLogger(__name__)


class BrowserManager:
    """
    Singleton browser manager that maintains a single browser instance
    with multiple contexts for efficient resource usage.
    
    CRITICAL: Always runs headless in production to prevent window spam.
    """
    
    _instance = None
    _lock = asyncio.Lock()
    _playwright: Optional[Playwright] = None
    _browser: Optional[Browser] = None
    _contexts: Dict[str, BrowserContext] = {}
    _pages: Dict[str, Page] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def initialize(self, headless: bool = True, proxy_list: Optional[List[str]] = None):
        """
        Initialize the browser with anti-detection measures.
        
        Args:
            headless: MUST be True in production to prevent window spam
            proxy_list: Optional list of proxy servers
        """
        async with self._lock:
            if self._browser is not None:
                logger.debug("Browser already initialized, reusing existing instance")
                return
            
            try:
                # Start Playwright
                self._playwright = await async_playwright().start()
                
                # Launch browser with stealth arguments
                logger.info(f"Launching browser (headless={headless})")
                self._browser = await self._playwright.chromium.launch(
                    headless=headless,  # ALWAYS True in production
                    args=self._get_stealth_args(),
                    # Don't use default Playwright user agent
                    ignore_default_args=['--enable-automation']
                )
                
                logger.info("Browser initialized successfully with anti-detection measures")
                
            except Exception as e:
                logger.error(f"Failed to initialize browser: {e}")
                raise
    
    def _get_stealth_args(self) -> List[str]:
        """Get browser launch arguments for stealth mode."""
        return [
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-accelerated-2d-canvas',
            '--disable-gpu',
            '--window-size=1920,1080',
            '--start-maximized',
            '--disable-infobars',
            '--disable-notifications',
            '--disable-popup-blocking',
            '--ignore-certificate-errors',
            '--allow-running-insecure-content'
        ]
    
    async def create_stealth_context(self, context_id: str = 'default',
                                   proxy: Optional[str] = None) -> BrowserContext:
        """
        Create a new browser context with anti-detection features.
        
        Args:
            context_id: Unique identifier for the context
            proxy: Optional proxy server URL
            
        Returns:
            Configured browser context
        """
        if not self._browser:
            await self.initialize()
        
        # Check if context already exists
        if context_id in self._contexts:
            logger.debug(f"Reusing existing context: {context_id}")
            return self._contexts[context_id]
        
        # Context configuration
        context_options = {
            'viewport': {'width': 1920, 'height': 1080},
            'user_agent': self._get_random_user_agent(),
            'locale': random.choice(['en-US', 'en-GB', 'en-CA']),
            'timezone_id': random.choice([
                'America/New_York',
                'America/Chicago', 
                'America/Los_Angeles',
                'America/Denver'
            ]),
            'permissions': ['geolocation', 'notifications'],
            'geolocation': self._get_random_geolocation(),
            'color_scheme': random.choice(['light', 'dark', 'no-preference']),
            'extra_http_headers': self._get_stealth_headers(),
            'ignore_https_errors': True,
            'java_script_enabled': True
        }
        
        # Add proxy if provided
        if proxy:
            context_options['proxy'] = {'server': proxy}
        
        # Create context
        context = await self._browser.new_context(**context_options)
        
        # Add stealth scripts to context
        await self._add_stealth_scripts(context)
        
        # Store context
        self._contexts[context_id] = context
        
        logger.info(f"Created stealth context: {context_id}")
        return context
    
    def _get_random_user_agent(self) -> str:
        """Get a random realistic user agent string."""
        user_agents = [
            # Chrome on Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            # Chrome on Mac
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            # Firefox on Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
            # Edge on Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0'
        ]
        return random.choice(user_agents)
    
    def _get_random_geolocation(self) -> Dict[str, float]:
        """Get random US geolocation."""
        locations = [
            {'latitude': 40.7128, 'longitude': -74.0060},  # New York
            {'latitude': 34.0522, 'longitude': -118.2437},  # Los Angeles
            {'latitude': 41.8781, 'longitude': -87.6298},   # Chicago
            {'latitude': 29.7604, 'longitude': -95.3698},   # Houston
            {'latitude': 33.4484, 'longitude': -112.0740},  # Phoenix
            {'latitude': 39.7392, 'longitude': -104.9903},  # Denver
            {'latitude': 47.6062, 'longitude': -122.3321},  # Seattle
            {'latitude': 25.7617, 'longitude': -80.1918},   # Miami
        ]
        return random.choice(locations)
    
    def _get_stealth_headers(self) -> Dict[str, str]:
        """Get stealth HTTP headers."""
        return {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        }
    
    async def _add_stealth_scripts(self, context: BrowserContext):
        """Add stealth JavaScript to bypass detection."""
        stealth_js = """
        // Override navigator.webdriver
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        
        // Override navigator.plugins to look realistic
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5].map(i => ({
                name: `Plugin ${i}`,
                description: `Description ${i}`,
                filename: `plugin${i}.dll`,
                length: 1
            }))
        });
        
        // Override navigator.languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en']
        });
        
        // Add chrome object
        if (!window.chrome) {
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };
        }
        
        // Override permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
        
        // Canvas fingerprinting protection
        const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function(type) {
            if (type === 'image/png' && this.width === 280 && this.height === 60) {
                // Return fake canvas fingerprint
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
        
        // Battery API protection
        if (navigator.getBattery) {
            navigator.getBattery = () => Promise.resolve({
                charging: true,
                chargingTime: 0,
                dischargingTime: Infinity,
                level: 1
            });
        }
        
        // Hardware concurrency randomization
        Object.defineProperty(navigator, 'hardwareConcurrency', {
            get: () => 4 + Math.floor(Math.random() * 4)
        });
        
        // Device memory
        Object.defineProperty(navigator, 'deviceMemory', {
            get: () => 8
        });
        
        // Max touch points
        Object.defineProperty(navigator, 'maxTouchPoints', {
            get: () => 0
        });
        """
        
        await context.add_init_script(stealth_js)
        logger.debug("Stealth scripts injected into context")
    
    async def get_page(self, context_id: str = 'default', 
                      page_id: Optional[str] = None) -> Page:
        """
        Get or create a page within a context.
        
        Args:
            context_id: Context identifier
            page_id: Optional page identifier for reuse
            
        Returns:
            Page instance
        """
        # Ensure context exists
        if context_id not in self._contexts:
            await self.create_stealth_context(context_id)
        
        context = self._contexts[context_id]
        
        # Create or get page
        if page_id and page_id in self._pages:
            page = self._pages[page_id]
            if not page.is_closed():
                logger.debug(f"Reusing existing page: {page_id}")
                return page
        
        # Create new page
        page = await context.new_page()
        
        # Store page if ID provided
        if page_id:
            self._pages[page_id] = page
        
        logger.debug(f"Created new page in context: {context_id}")
        return page
    
    async def close_page(self, page_id: str):
        """Close a specific page."""
        if page_id in self._pages:
            page = self._pages[page_id]
            if not page.is_closed():
                await page.close()
            del self._pages[page_id]
            logger.debug(f"Closed page: {page_id}")
    
    async def close_context(self, context_id: str):
        """Close a specific context and all its pages."""
        if context_id in self._contexts:
            context = self._contexts[context_id]
            await context.close()
            del self._contexts[context_id]
            
            # Remove pages associated with this context
            pages_to_remove = []
            for page_id, page in self._pages.items():
                if page.context == context:
                    pages_to_remove.append(page_id)
            
            for page_id in pages_to_remove:
                del self._pages[page_id]
            
            logger.info(f"Closed context: {context_id}")
    
    async def cleanup(self):
        """Clean up all resources."""
        try:
            # Close all pages
            for page_id in list(self._pages.keys()):
                await self.close_page(page_id)
            
            # Close all contexts
            for context_id in list(self._contexts.keys()):
                await self.close_context(context_id)
            
            # Close browser
            if self._browser:
                await self._browser.close()
                self._browser = None
            
            # Stop playwright
            if self._playwright:
                await self._playwright.stop()
                self._playwright = None
            
            logger.info("Browser manager cleaned up successfully")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    @asynccontextmanager
    async def get_page_context(self, context_id: str = 'default',
                              page_id: Optional[str] = None):
        """
        Context manager for automatic page cleanup.
        
        Usage:
            async with browser_manager.get_page_context() as page:
                await page.goto('https://example.com')
        """
        page = await self.get_page(context_id, page_id)
        try:
            yield page
        finally:
            if page_id:
                await self.close_page(page_id)
            elif not page.is_closed():
                await page.close()


class HumanBehaviorSimulator:
    """Simulate human-like browsing patterns to avoid detection."""
    
    @staticmethod
    async def random_delay(min_seconds: float = 0.5, max_seconds: float = 2.0):
        """Add random delay between actions."""
        delay = random.uniform(min_seconds, max_seconds)
        await asyncio.sleep(delay)
    
    @staticmethod
    async def human_type(page: Page, selector: str, text: str, 
                        chars_per_minute: int = 280):
        """
        Type text with human-like speed and patterns.
        
        Args:
            page: Page to type on
            selector: Element selector
            text: Text to type
            chars_per_minute: Typing speed
        """
        element = await page.query_selector(selector)
        if not element:
            logger.warning(f"Element not found: {selector}")
            return
        
        await element.click()
        
        # Calculate delay between keystrokes
        delay_ms = 60000 / chars_per_minute
        
        for char in text:
            await element.type(char, delay=random.uniform(delay_ms * 0.5, delay_ms * 1.5))
            
            # Occasional longer pauses (thinking)
            if random.random() < 0.05:
                await asyncio.sleep(random.uniform(0.5, 1.5))
            
            # Natural pauses after punctuation
            if char in '.,!?;:':
                await asyncio.sleep(random.uniform(0.2, 0.5))
    
    @staticmethod
    async def human_click(page: Page, selector: str):
        """Click with natural mouse movement."""
        element = await page.query_selector(selector)
        if not element:
            logger.warning(f"Element not found for click: {selector}")
            return
        
        # Get element position
        box = await element.bounding_box()
        if not box:
            await element.click()
            return
        
        # Calculate random point within element
        x = box['x'] + random.uniform(5, box['width'] - 5)
        y = box['y'] + random.uniform(5, box['height'] - 5)
        
        # Move mouse with curve
        await page.mouse.move(x, y, steps=random.randint(5, 10))
        await HumanBehaviorSimulator.random_delay(0.1, 0.3)
        await page.mouse.click(x, y)
    
    @staticmethod
    async def simulate_reading(page: Page, duration_seconds: float = None):
        """
        Simulate reading behavior with scrolling.
        
        Args:
            page: Page to scroll
            duration_seconds: How long to "read" (random if None)
        """
        if duration_seconds is None:
            duration_seconds = random.uniform(2, 5)
        
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < duration_seconds:
            # Random scroll distance
            scroll_distance = random.randint(100, 500)
            
            # Scroll down
            await page.evaluate(f'window.scrollBy(0, {scroll_distance})')
            
            # Reading pause
            await HumanBehaviorSimulator.random_delay(0.5, 2)
            
            # Occasionally scroll up a bit (re-reading)
            if random.random() < 0.2:
                await page.evaluate(f'window.scrollBy(0, -{random.randint(50, 150)})')
                await HumanBehaviorSimulator.random_delay(0.3, 0.8)
    
    @staticmethod
    async def move_mouse_naturally(page: Page, movements: int = None):
        """
        Simulate natural mouse movements.
        
        Args:
            page: Page to move mouse on
            movements: Number of movements (random if None)
        """
        if movements is None:
            movements = random.randint(2, 5)
        
        viewport = page.viewport_size
        if not viewport:
            return
        
        for _ in range(movements):
            x = random.randint(0, viewport['width'])
            y = random.randint(0, viewport['height'])
            steps = random.randint(5, 15)
            
            await page.mouse.move(x, y, steps=steps)
            await HumanBehaviorSimulator.random_delay(0.1, 0.5)


async def detect_honeypots(page: Page) -> List[Any]:
    """
    Detect and return honeypot elements on the page.
    
    Args:
        page: Page to check
        
    Returns:
        List of honeypot elements to avoid
    """
    honeypots = []
    
    # Find all interactive elements
    elements = await page.query_selector_all('a, input, button, textarea, select')
    
    for element in elements:
        try:
            # Check if element is visible
            is_visible = await element.is_visible()
            
            # Check computed styles
            is_honeypot = await element.evaluate("""
                (element) => {
                    const style = window.getComputedStyle(element);
                    const rect = element.getBoundingClientRect();
                    
                    // Check for hidden elements
                    if (style.display === 'none' || 
                        style.visibility === 'hidden' ||
                        parseFloat(style.opacity) === 0 ||
                        rect.width === 0 || 
                        rect.height === 0) {
                        return true;
                    }
                    
                    // Check for off-screen elements
                    if (rect.left < -9999 || rect.top < -9999) {
                        return true;
                    }
                    
                    // Check for elements with suspicious classes/ids
                    const suspicious = ['honeypot', 'trap', 'hidden', 'invisible'];
                    const classAndId = (element.className + ' ' + element.id).toLowerCase();
                    
                    return suspicious.some(term => classAndId.includes(term));
                }
            """)
            
            if is_honeypot or not is_visible:
                honeypots.append(element)
                
        except Exception as e:
            logger.debug(f"Error checking element for honeypot: {e}")
    
    if honeypots:
        logger.info(f"Detected {len(honeypots)} honeypot elements")
    
    return honeypots


# Singleton instance
browser_manager = BrowserManager()