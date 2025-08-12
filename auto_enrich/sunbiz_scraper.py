"""
Dedicated Sunbiz.org scraper using Playwright for Florida corporate records.
This scraper navigates to the search page, enters the business name, and extracts
officer/director information from the corporate record.
"""

import asyncio
import logging
import re
from typing import Dict, Any, Optional, List
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class SunbizScraper:
    """
    Scraper for Florida's Sunbiz.org corporate records.
    Uses Playwright to navigate and extract officer information.
    """
    
    def __init__(self):
        """Initialize the Sunbiz scraper."""
        self.base_url = "https://search.sunbiz.org"
        self.search_url = f"{self.base_url}/Inquiry/CorporationSearch/ByName"
        
    async def search_business(self, business_name: str) -> Optional[Dict[str, Any]]:
        """
        Search for a business on Sunbiz.org and extract corporate information.
        
        Args:
            business_name: The legal name of the business
            
        Returns:
            Dictionary with corporate information including officers
        """
        try:
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                # Launch browser with more realistic settings
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--no-sandbox'
                    ]
                )
                
                # Create context with full user agent and viewport
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={'width': 1920, 'height': 1080},
                    locale='en-US',
                    timezone_id='America/New_York'
                )
                
                # Add anti-detection scripts
                await context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                """)
                
                page = await context.new_page()
                
                # Navigate to search page with more natural timing
                logger.info(f"Navigating to Sunbiz search for: {business_name}")
                await page.goto(self.search_url, wait_until='domcontentloaded')
                
                # Small delay to appear more human
                await page.wait_for_timeout(1000)
                
                # Click on the search field first (more human-like)
                search_input = await page.wait_for_selector('input[name="SearchTerm"]', timeout=5000)
                await search_input.click()
                
                # Small delay before typing
                await page.wait_for_timeout(500)
                
                # Type the business name with realistic typing speed
                await search_input.type(business_name, delay=50)
                
                # Small delay before submitting
                await page.wait_for_timeout(500)
                
                # Submit by clicking the Search Now button instead of pressing Enter
                search_button = await page.query_selector('input[type="submit"][value="Search Now"]')
                if search_button:
                    await search_button.click()
                else:
                    # Fallback to Enter key
                    await page.press('input[name="SearchTerm"]', 'Enter')
                
                # Wait for navigation
                await page.wait_for_load_state('networkidle', timeout=10000)
                
                # Look for result links directly (more reliable than table.SearchResults)
                # Sunbiz puts results as links with 'SearchResultDetail' in the href
                result_links = await page.query_selector_all('a[href*="SearchResultDetail"]')
                
                if not result_links:
                    logger.warning(f"No results found for: {business_name}")
                    await browser.close()
                    return None
                
                logger.info(f"Found {len(result_links)} potential matches")
                
                # Find the best matching result
                best_match_link = None
                
                for link in result_links:
                    name_text = await link.inner_text()
                    
                    # Sunbiz may display names with slight punctuation differences
                    name_text_clean = name_text.strip().upper()
                    business_name_clean = business_name.strip().upper()
                    
                    # Limited normalization - only handle common Sunbiz punctuation variations:
                    # 1. Remove commas (Sunbiz adds comma before INC, LLC, etc.)
                    # 2. Remove periods (L.L.C. vs LLC, INC. vs INC)
                    # 3. Remove apostrophes (BOB'S vs BOBS)
                    # 4. Normalize multiple spaces to single space
                    def normalize_for_sunbiz(text):
                        return ' '.join(text.replace(',', '')
                                          .replace('.', '')
                                          .replace("'", '')
                                          .split())
                    
                    name_text_normalized = normalize_for_sunbiz(name_text_clean)
                    business_name_normalized = normalize_for_sunbiz(business_name_clean)
                    
                    # Check for match after minimal normalization
                    if name_text_normalized == business_name_normalized:
                        best_match_link = link
                        logger.info(f"Found match: {name_text}")
                        break
                    
                    # Check if this might be a truncated match
                    # Sunbiz typically shows about 100 characters max in the results
                    elif len(name_text_clean) >= 95 and business_name_normalized.startswith(name_text_normalized):
                        # The displayed name might be truncated
                        best_match_link = link
                        logger.info(f"Found potential truncated match: {name_text}")
                        break
                
                if not best_match_link:
                    logger.warning(f"No exact match found for: {business_name}")
                    await browser.close()
                    return None
                
                # Click on the matching result
                await best_match_link.click()
                await page.wait_for_load_state('networkidle')
                
                # Extract information from the detail page
                result = await self._extract_corporate_info(page)
                
                await browser.close()
                return result
                
        except Exception as e:
            logger.error(f"Error scraping Sunbiz for {business_name}: {e}")
            return None
    
    async def _extract_corporate_info(self, page) -> Dict[str, Any]:
        """
        Extract corporate information from a Sunbiz detail page.
        
        Args:
            page: Playwright page object on the detail page
            
        Returns:
            Dictionary with extracted information
        """
        info = {
            'company_name': '',
            'entity_type': '',
            'officers': [],
            'authorized_persons': [],
            'registered_agent': {},
            'filing_info': {},
            'principal_address': {},
            'mailing_address': {},
            'annual_reports': []
        }
        
        try:
            # Extract company name and type from the top section
            corp_name_section = await page.query_selector('.detailSection.corporationName')
            if corp_name_section:
                text = await corp_name_section.inner_text()
                lines = [l.strip() for l in text.split('\n') if l.strip()]
                if lines:
                    info['entity_type'] = lines[0] if len(lines) > 0 else ''
                    info['company_name'] = lines[1] if len(lines) > 1 else ''
            
            # Extract filing information - parse the entire HTML structure
            filing_section = await page.query_selector('.detailSection.filingInformation')
            if filing_section:
                # Get the HTML and parse it properly
                section_html = await filing_section.inner_html()
                
                # Extract using text patterns since the structure is consistent
                section_text = await filing_section.inner_text()
                lines = [l.strip() for l in section_text.splitlines() if l.strip()]
                
                # Parse the lines looking for key:value patterns
                for i, line in enumerate(lines):
                    if 'Document Number' in line and i + 1 < len(lines):
                        info['filing_info']['document_number'] = lines[i + 1]
                    elif 'FEI/EIN Number' in line and i + 1 < len(lines):
                        info['filing_info']['fein'] = lines[i + 1]
                    elif 'Date Filed' in line and i + 1 < len(lines):
                        info['filing_info']['date_filed'] = lines[i + 1]  # Company start date!
                    elif line == 'State' and i + 1 < len(lines):
                        info['filing_info']['state'] = lines[i + 1]
                    elif 'Status' in line and i + 1 < len(lines):
                        info['filing_info']['status'] = lines[i + 1]
                    elif 'Last Event' in line and 'Date' not in line and i + 1 < len(lines):
                        info['filing_info']['last_event'] = lines[i + 1]
            
            # Extract Principal Address
            principal_sections = await page.query_selector_all('.detailSection')
            for section in principal_sections:
                header = await section.query_selector('span')
                if header:
                    header_text = await header.inner_text()
                    
                    if header_text == 'Principal Address':
                        address_div = await section.query_selector('div')
                        if address_div:
                            info['principal_address']['full'] = await address_div.inner_text()
                    
                    elif header_text == 'Mailing Address':
                        address_div = await section.query_selector('div')
                        if address_div:
                            info['mailing_address']['full'] = await address_div.inner_text()
            
            # Extract Registered Agent Name & Address
            agent_section = await page.query_selector('span:text("Registered Agent Name & Address")')
            if agent_section:
                parent = await agent_section.evaluate_handle('(el) => el.parentElement')
                if parent:
                    all_spans = await parent.query_selector_all('span')
                    # Second span should be the agent name
                    if len(all_spans) > 1:
                        info['registered_agent']['name'] = await all_spans[1].inner_text()
                    # Third span should have the address
                    if len(all_spans) > 2:
                        address_div = await all_spans[2].query_selector('div')
                        if address_div:
                            info['registered_agent']['address'] = await address_div.inner_text()
            
            # Extract Authorized Person(s) - this is often the owner/officers
            auth_section = await page.query_selector('span:text("Authorized Person(s) Detail")')
            if auth_section:
                parent = await auth_section.evaluate_handle('(el) => el.parentElement')
                if parent:
                    text = await parent.inner_text()
                    # Split on newlines - inner_text returns actual newline characters
                    lines = [l.strip() for l in text.splitlines() if l.strip()]
                    
                    current_person = {}
                    
                    for i, line in enumerate(lines):
                        # Skip headers and section titles
                        if 'Authorized Person' in line or 'Name & Address' in line:
                            continue
                        
                        # Look for Title line (format: "Title MGR" or "Title MGRM")
                        # Note: Sunbiz uses non-breaking space (\xa0) between Title and value
                        if line.startswith('Title'):
                            # Save previous person if exists
                            if current_person and 'full_name' in current_person:
                                info['authorized_persons'].append(current_person)
                            
                            # Extract title - handle both regular and non-breaking spaces
                            line_clean = line.replace('\xa0', ' ')  # Replace non-breaking space
                            title_parts = line_clean.split(None, 1)  # Split on first whitespace
                            if len(title_parts) > 1:
                                current_person = {'title': title_parts[1]}
                        
                        # Look for name line (comes after title, before address)
                        elif current_person and 'title' in current_person and 'full_name' not in current_person:
                            # Skip if this looks like an address line with street suffix
                            # More specific check - only skip if it has numbers AND street suffix
                            if re.search(r'\d+.*\b(AVE|ST|RD|BLVD|DR|LANE|CT|WAY|PKWY|PLAZA|CIRCLE|PLACE)\b', line, re.IGNORECASE):
                                continue
                            # Skip if line contains state abbreviation and zip (address pattern)
                            if re.search(r'\b[A-Z]{2}\s+\d{5}', line):
                                continue
                            # Skip if line is just numbers (likely street number)
                            if line.replace(' ', '').isdigit():
                                continue
                                
                            # This should be a name
                            if ',' in line:  # Format: "LAST, FIRST"
                                parts = line.split(',', 1)
                                current_person['last_name'] = parts[0].strip()
                                current_person['first_name'] = parts[1].strip() if len(parts) > 1 else ''
                                current_person['full_name'] = line
                            elif line and len(line) > 2:  # Just a name without comma
                                # Try to split into first/last
                                name_parts = line.split()
                                if len(name_parts) >= 2:
                                    current_person['first_name'] = name_parts[0]
                                    current_person['last_name'] = ' '.join(name_parts[1:])
                                else:
                                    current_person['first_name'] = ''
                                    current_person['last_name'] = line
                                current_person['full_name'] = line
                    
                    # Add last person if exists
                    if current_person and 'full_name' in current_person:
                        info['authorized_persons'].append(current_person)
            
            # For corporations, also check for Officer/Director Detail
            officer_section = await page.query_selector('span:text("Officer/Director Detail")')
            if officer_section:
                parent = await officer_section.evaluate_handle('(el) => el.parentElement')
                if parent:
                    text = await parent.inner_text()
                    lines = [l.strip() for l in text.splitlines() if l.strip()]
                    
                    current_officer = {}
                    
                    for i, line in enumerate(lines):
                        # Skip headers
                        if 'Officer/Director' in line or 'Name & Address' in line:
                            continue
                        
                        # Look for Title line (could be "Title PRES" or standalone "Title" with value on next line)
                        if line.startswith('Title'):
                            # Save previous officer if exists
                            if current_officer and 'full_name' in current_officer:
                                info['officers'].append(current_officer)
                            
                            # Handle non-breaking spaces from Sunbiz
                            line_clean = line.replace('\xa0', ' ')
                            # Check if title is on same line or next line
                            title_parts = line_clean.split(None, 1)
                            if len(title_parts) > 1:
                                # Title on same line (LLC format)
                                current_officer = {'title': title_parts[1]}
                            elif i + 1 < len(lines):
                                # Title on next line (Corp format)
                                current_officer = {'title': lines[i + 1]}
                        
                        # Look for name line (comes after title, before address)
                        elif current_officer and 'title' in current_officer and 'full_name' not in current_officer:
                            # Skip if this is the title value we already captured
                            if line == current_officer.get('title'):
                                continue
                            # Skip if this looks like an address line
                            if any(x in line.lower() for x in ['ave', 'st', 'rd', 'blvd', 'dr', 'lane', 'suite', 'ct', 'way', 'pkwy', 'plaza']):
                                continue
                            # Skip if line contains state abbreviation and zip
                            if re.search(r'\b[A-Z]{2}\s+\d{5}', line):
                                continue
                            # Skip if line is just numbers
                            if line.replace(' ', '').isdigit():
                                continue
                                
                            # This should be a name
                            if ',' in line:  # Format: "LAST, FIRST"
                                parts = line.split(',', 1)
                                current_officer['last_name'] = parts[0].strip()
                                current_officer['first_name'] = parts[1].strip() if len(parts) > 1 else ''
                                current_officer['full_name'] = line
                            elif line and len(line) > 2:  # Just a name
                                # Try to split into first/last
                                name_parts = line.split()
                                if len(name_parts) >= 2:
                                    current_officer['first_name'] = name_parts[0]
                                    current_officer['last_name'] = ' '.join(name_parts[1:])
                                else:
                                    current_officer['first_name'] = ''
                                    current_officer['last_name'] = line
                                current_officer['full_name'] = line
                    
                    # Add last officer if exists
                    if current_officer and 'full_name' in current_officer:
                        info['officers'].append(current_officer)
            
            # Remove annual reports extraction per user request
            # User said: "You do not need annual report tables"
            
            # Combine officers and authorized persons for owner detection
            all_persons = info['officers'] + info['authorized_persons']
            
            logger.info(f"Extracted {len(info['officers'])} officers and {len(info['authorized_persons'])} authorized persons from Sunbiz")
            logger.info(f"Company filed on: {info['filing_info'].get('date_filed', 'Unknown')}")
            logger.info(f"FEIN: {info['filing_info'].get('fein', 'Not found')}")
            
        except Exception as e:
            logger.error(f"Error extracting corporate info: {e}")
        
        return info


# Helper function for testing
async def test_sunbiz_scraper():
    """Test the Sunbiz scraper with a known business."""
    scraper = SunbizScraper()
    
    # Test with a known Florida business
    result = await scraper.search_business("GATOR CITY MOTORS LLC")
    
    if result:
        print("\n=== Sunbiz Scraper Test Results ===")
        print(f"Officers found: {len(result['officers'])}")
        for officer in result['officers']:
            print(f"  - {officer.get('full_name', 'Unknown')} ({officer.get('title', 'Unknown')})")
        
        if result['registered_agent']:
            print(f"\nRegistered Agent: {result['registered_agent'].get('name', 'Unknown')}")
        
        print(f"\nAnnual Reports Filed: {result['annual_reports']}")
    else:
        print("No results found")
    
    return result


if __name__ == "__main__":
    # Test the scraper
    asyncio.run(test_sunbiz_scraper())