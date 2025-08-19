#!/usr/bin/env python3
"""
Diagnose why we're getting low content from the website.
"""

import asyncio
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def diagnose_site():
    """Diagnose what's happening with the site."""
    from playwright.async_api import async_playwright
    
    url = "http://www.gatorcitymotors.com"
    print(f"\nDiagnosing: {url}")
    print("="*60)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,  # Run headless
            args=['--disable-blink-features=AutomationControlled']
        )
        
        context = await browser.new_context()
        page = await context.new_page()
        
        # Navigate
        print("1. Navigating to page...")
        response = await page.goto(url, wait_until='domcontentloaded')
        print(f"   Response status: {response.status}")
        
        # Wait a bit
        await asyncio.sleep(3)
        
        # Check for various protection mechanisms
        print("\n2. Checking for protection mechanisms...")
        
        # Check for Cloudflare
        cloudflare_check = await page.evaluate("""() => {
            const cfElements = document.querySelectorAll('[class*="cloudflare"], [id*="cloudflare"]');
            const cfChallenge = document.querySelector('.challenge-form');
            const cfRay = document.querySelector('[data-cf-ray]');
            return {
                hasCloudflareElements: cfElements.length > 0,
                hasChallengeForm: cfChallenge !== null,
                hasCfRay: cfRay !== null,
                title: document.title,
                titleHasCloudflare: document.title.toLowerCase().includes('cloudflare')
            };
        }""")
        
        print(f"   Cloudflare elements: {cloudflare_check['hasCloudflareElements']}")
        print(f"   Challenge form: {cloudflare_check['hasChallengeForm']}")
        print(f"   CF-Ray header: {cloudflare_check['hasCfRay']}")
        print(f"   Title has Cloudflare: {cloudflare_check['titleHasCloudflare']}")
        print(f"   Page title: {cloudflare_check['title']}")
        
        # Check for iframes
        print("\n3. Checking for iframes...")
        iframe_info = await page.evaluate("""() => {
            const iframes = document.querySelectorAll('iframe');
            return {
                count: iframes.length,
                sources: Array.from(iframes).map(f => f.src || 'no-src').slice(0, 3)
            };
        }""")
        print(f"   Iframes found: {iframe_info['count']}")
        if iframe_info['sources']:
            print(f"   Sources: {iframe_info['sources']}")
        
        # Check content structure
        print("\n4. Analyzing content structure...")
        content_analysis = await page.evaluate("""() => {
            const body = document.body;
            const main = document.querySelector('main') || document.querySelector('[role="main"]');
            const contentDivs = document.querySelectorAll('div.content, #content, .main-content');
            
            // Get text from different methods
            const bodyText = body.innerText || '';
            const bodyTextContent = body.textContent || '';
            const htmlLength = document.documentElement.outerHTML.length;
            
            // Check for hidden content
            const hiddenElements = document.querySelectorAll('[style*="display:none"], [style*="visibility:hidden"], .hidden');
            
            return {
                bodyInnerTextLength: bodyText.length,
                bodyTextContentLength: bodyTextContent.length,
                htmlLength: htmlLength,
                hasMainElement: main !== null,
                contentDivsCount: contentDivs.length,
                hiddenElementsCount: hiddenElements.length,
                bodyChildrenCount: body.children.length,
                scriptTags: document.querySelectorAll('script').length,
                styleTags: document.querySelectorAll('style').length
            };
        }""")
        
        for key, value in content_analysis.items():
            print(f"   {key}: {value}")
        
        # Check for JavaScript rendering
        print("\n5. Checking JavaScript rendering...")
        
        # Wait for potential JavaScript to load content
        await asyncio.sleep(5)
        
        content_after_wait = await page.evaluate("""() => {
            return {
                bodyTextAfterWait: (document.body.innerText || '').length,
                dynamicElementsCount: document.querySelectorAll('[data-react], [data-vue], [ng-], [v-]').length
            };
        }""")
        
        print(f"   Body text after 5s wait: {content_after_wait['bodyTextAfterWait']} chars")
        print(f"   Dynamic framework elements: {content_after_wait['dynamicElementsCount']}")
        
        # Try to get actual visible text
        print("\n6. Extracting visible text...")
        visible_text = await page.evaluate("""() => {
            function isVisible(elem) {
                if (!elem) return false;
                const style = window.getComputedStyle(elem);
                return style.display !== 'none' && 
                       style.visibility !== 'hidden' && 
                       style.opacity !== '0';
            }
            
            function getVisibleText(element) {
                let text = '';
                if (element.nodeType === Node.TEXT_NODE) {
                    if (isVisible(element.parentElement)) {
                        text = element.textContent;
                    }
                } else if (element.nodeType === Node.ELEMENT_NODE) {
                    if (isVisible(element)) {
                        for (let child of element.childNodes) {
                            text += getVisibleText(child);
                        }
                    }
                }
                return text;
            }
            
            return getVisibleText(document.body).length;
        }""")
        
        print(f"   Visible text length: {visible_text} chars")
        
        # Take a screenshot for visual inspection
        await page.screenshot(path="diagnostic_screenshot.png")
        print("\n7. Screenshot saved as 'diagnostic_screenshot.png'")
        
        # Get page source
        page_source = await page.content()
        with open("diagnostic_page_source.html", "w", encoding="utf-8") as f:
            f.write(page_source)
        print("8. Page source saved as 'diagnostic_page_source.html'")
        
        # Keep browser open for manual inspection
        print("\n" + "="*60)
        print("DIAGNOSIS COMPLETE")
        print("Browser will stay open for 10 seconds for manual inspection...")
        print("="*60)
        
        await asyncio.sleep(10)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(diagnose_site())