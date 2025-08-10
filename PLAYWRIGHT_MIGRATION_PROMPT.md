# Selenium to Playwright Migration - Structured Prompt for AI Agent

## PROJECT CONTEXT
You are tasked with migrating a web scraping system from Selenium to Playwright in a Personalized Email Marketing application. The system currently uses Selenium with real Chrome browsers which is causing issues:
- Opening hundreds of browser windows
- Getting detected as a bot by Google and other sites
- Poor resource management
- No proper anti-detection measures

## CRITICAL REQUIREMENTS
1. **NEVER** open visible browser windows - always use `headless=True`
2. **SINGLE BROWSER INSTANCE** - Use one browser with multiple pages, not multiple browsers
3. **IMPLEMENT ANTI-DETECTION** - Use all techniques from `docs/MODERN_WEB_SCRAPING_TECHNIQUES.md`
4. **MAINTAIN FUNCTIONALITY** - The system must continue to work with existing API and data flow

## FILES TO MIGRATE

### PRIMARY SELENIUM FILES (Must Replace)
1. **`auto_enrich/search_with_selenium.py`**
   - Class: `RealChromeSearch`
   - Main function: `search_with_real_chrome()`
   - Currently uses Selenium WebDriver with ChromeDriverManager
   - Opens visible Chrome browser causing window spam issue

2. **`auto_enrich/web_scraper_selenium.py`**
   - Class: `WebScraperSelenium`
   - Uses Selenium for scraping websites
   - Needs complete rewrite with Playwright

3. **`test_selenium_direct.py`**
   - Test file using Selenium directly
   - Convert to Playwright tests

4. **`test_selenium_mcp.py`**
   - Test file for Selenium with MCP integration
   - Update to use Playwright

### SEARCH ENGINE IMPLEMENTATIONS (May Need Updates)
1. **`auto_enrich/search_engines.py`**
   - Classes: `GoogleSearch`, `DuckDuckGoSearch`, `BingSearch`, `MultiEngineSearch`
   - Check for any browser automation code

2. **`auto_enrich/search_engines_improved.py`**
   - Class: `GoogleSearchImproved` - Has `_search_via_playwright()` method
   - Already has some Playwright code - verify and enhance

3. **`auto_enrich/scraper.py`**
   - Has `_search_google()` function
   - Check browser usage

### SUPPORTING FILES (Review for Integration)
1. **`auto_enrich/web_scraper.py`** - Main scraper interface
2. **`auto_enrich/web_scraper_old.py`** - Legacy code, may be removed
3. **`auto_enrich/mcp_client.py`** - MCP integration for HTML to Markdown
4. **`auto_enrich/enricher.py`** - Main enrichment orchestrator
5. **`auto_enrich/data_interpreter.py`** - Data processing
6. **`auto_enrich/profile_builder.py`** - Profile construction

### TEST FILES (Update After Migration)
- `test_complete_system.py`
- `test_enhanced_integration.py`
- `test_known_dealer.py`
- `test_real_dealer.py`
- `test_single_enrichment.py`
- `test_multi_source.py`
- `test_mcp_config.py`

## IMPLEMENTATION STRATEGY

### Phase 1: Core Migration
1. **Create `auto_enrich/playwright_browser_manager.py`**
   ```python
   # Singleton browser manager
   # Implements patterns from MODERN_WEB_SCRAPING_TECHNIQUES.md
   # Single browser instance with context pool
   # Anti-detection measures built-in
   ```

2. **Replace `search_with_selenium.py` with `search_with_playwright.py`**
   - Implement `PlaywrightSearch` class
   - Use humanization techniques
   - Add anti-fingerprinting
   - MUST run headless

3. **Replace `web_scraper_selenium.py` with `web_scraper_playwright.py`**
   - Implement `WebScraperPlaywright` class
   - Integrate with MCP for HTML→Markdown conversion
   - Add honeypot detection
   - Implement retry logic

### Phase 2: Library Installation
```python
# Required libraries (add to requirements.txt)
playwright>=1.40.0
humanization-playwright>=0.1.0
crawlee[playwright]>=0.3.0
```

### Phase 3: Anti-Detection Implementation
Implement ALL techniques from `docs/MODERN_WEB_SCRAPING_TECHNIQUES.md`:
- Browser fingerprint randomization
- Human-like mouse movements and typing
- Random delays and scrolling patterns
- Proxy rotation (if configured)
- Stealth mode initialization scripts

### Phase 4: Testing & Validation
1. Update all test files to use Playwright
2. Verify no browser windows open during execution
3. Test anti-bot detection with Google searches
4. Performance benchmarking

## KEY PATTERNS TO IMPLEMENT

### 1. Browser Lifecycle Management
```python
class BrowserManager:
    _instance = None
    _browser = None
    
    @classmethod
    async def get_browser(cls):
        if not cls._browser:
            playwright = await async_playwright().start()
            cls._browser = await playwright.chromium.launch(
                headless=True,  # CRITICAL: Always True
                args=['--disable-blink-features=AutomationControlled']
            )
        return cls._browser
```

### 2. Search Implementation
```python
async def search_google_playwright(query: str) -> List[Dict]:
    browser = await BrowserManager.get_browser()
    context = await browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent=get_random_user_agent()
    )
    page = await context.new_page()
    
    try:
        # Add stealth scripts
        await add_stealth_scripts(page)
        
        # Navigate with human-like behavior
        await page.goto('https://google.com')
        await human_type(page, 'textarea[name="q"]', query)
        await human_click(page, 'button[type="submit"]')
        
        # Extract results
        results = await extract_search_results(page)
        return results
    finally:
        await page.close()
        await context.close()
```

### 3. Scraping Implementation
```python
async def scrape_with_playwright(url: str) -> Dict:
    browser = await BrowserManager.get_browser()
    context = await create_stealth_context(browser)
    page = await context.new_page()
    
    try:
        # Navigate with timeout
        await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        
        # Detect and avoid honeypots
        honeypots = await detect_honeypots(page)
        
        # Simulate human behavior
        await simulate_reading(page)
        
        # Extract content
        content = await page.content()
        
        # Convert to markdown via MCP
        markdown = await mcp_client.html_to_markdown(content)
        
        return {'url': url, 'content': markdown}
    finally:
        await page.close()
        await context.close()
```

## VALIDATION CHECKLIST
- [ ] No browser windows open during execution
- [ ] All Selenium imports removed
- [ ] webdriver_manager dependencies removed
- [ ] Playwright properly installed via `playwright install`
- [ ] Anti-detection measures implemented
- [ ] Single browser instance pattern used
- [ ] All tests pass with new implementation
- [ ] Google searches work without bot detection
- [ ] Resource cleanup properly implemented
- [ ] Error handling and retries in place

## IMPORTANT NOTES
1. **Headless Mode**: MUST always be `True` in production
2. **Browser Reuse**: Create browser once, reuse for all operations
3. **Context Isolation**: Use separate contexts for different tasks
4. **Cleanup**: Always close pages and contexts after use
5. **MCP Integration**: Continue using MCP Fetch for HTML→Markdown (no API costs)

## EXPECTED OUTCOME
After migration:
- Zero visible browser windows
- Improved scraping success rate
- Better anti-bot detection evasion
- Lower resource usage
- Faster execution
- Maintainable codebase with modern practices

## REFERENCE DOCUMENTATION
- Main guide: `docs/MODERN_WEB_SCRAPING_TECHNIQUES.md`
- Current architecture: `CLAUDE.md`
- MCP integration: `docs/mcp-integration-strategy.md`

---

**START HERE**: Begin with Phase 1 - Create the browser manager module, then systematically replace Selenium files with Playwright equivalents while ensuring no browser windows are ever visible.