#!/usr/bin/env python3
"""
Patch to fix the Sunbiz scraper to properly detect addresses vs names.
This creates a fixed version without modifying the original.
"""

import asyncio
import logging
import re
from typing import Dict, Any, Optional, List
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class SunbizScraperFixed:
    """
    Fixed version of Sunbiz scraper that properly distinguishes addresses from names.
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
                
                # Look for result links directly
                result_links = await page.query_selector_all('a[href*="SearchResultDetail"]')
                
                if not result_links:
                    logger.warning(f"No results found for: {business_name}")
                    await browser.close()
                    return None
                
                logger.info(f"Found {len(result_links)} potential matches")
                
                # OPTIMIZATION: Take the first result (most relevant by Sunbiz ranking)
                # Sunbiz returns results ordered by relevance, so first match is typically best
                best_match_link = result_links[0]
                best_match_text = await best_match_link.inner_text()
                logger.info(f"Taking first match from {len(result_links)} results: {best_match_text}")
                
                # Optional: Quick validation that first result contains key words from business name
                business_words = set(business_name.upper().split())
                result_words = set(best_match_text.upper().split())
                common_words = business_words & result_words
                
                if len(common_words) == 0:
                    logger.warning(f"First result '{best_match_text}' has no common words with '{business_name}' - may be incorrect match")
                else:
                    logger.info(f"First result has {len(common_words)} common words - looks good")
                
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
    
    def _is_likely_address_line(self, line: str) -> bool:
        """
        Check if a line is likely an address rather than a person's name.
        More precise than checking for substrings.
        """
        line_lower = line.lower()
        
        # Street suffixes that indicate an address - check as whole words
        street_suffixes = [
            'ave', 'avenue', 'st', 'street', 'rd', 'road', 'blvd', 'boulevard',
            'dr', 'drive', 'ln', 'lane', 'ct', 'court', 'way', 'pkwy', 'parkway',
            'plaza', 'circle', 'place', 'terr', 'terrace', 'trail', 'hwy', 'highway'
        ]
        
        # Check for street suffixes as whole words (with word boundaries)
        for suffix in street_suffixes:
            # Check if suffix appears as a whole word
            if re.search(r'\b' + suffix + r'\b', line_lower):
                return True
        
        # Additional checks for common address patterns
        if re.search(r'\b(suite|ste|apt|unit|floor|fl)\b', line_lower):
            return True
            
        # Check if line starts with numbers followed by text (common address pattern)
        if re.match(r'^\d+\s+\w+', line):
            # But exclude cases like "1ST PRESIDENT" or "2ND DIRECTOR"
            if not re.search(r'\d+(st|nd|rd|th)\s+(president|director|vice|secretary|treasurer)', line_lower):
                return True
        
        return False
    
    async def _extract_corporate_info(self, page) -> Dict[str, Any]:
        """
        Extract corporate information from a Sunbiz detail page.
        Fixed version with better address detection.
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
            
            # Extract filing information
            filing_section = await page.query_selector('.detailSection.filingInformation')
            if filing_section:
                section_text = await filing_section.inner_text()
                lines = [l.strip() for l in section_text.splitlines() if l.strip()]
                
                for i, line in enumerate(lines):
                    if 'Document Number' in line and i + 1 < len(lines):
                        info['filing_info']['document_number'] = lines[i + 1]
                    elif 'FEI/EIN Number' in line and i + 1 < len(lines):
                        info['filing_info']['fein'] = lines[i + 1]
                    elif 'Date Filed' in line and i + 1 < len(lines):
                        info['filing_info']['date_filed'] = lines[i + 1]
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
                    if len(all_spans) > 1:
                        info['registered_agent']['name'] = await all_spans[1].inner_text()
                    if len(all_spans) > 2:
                        address_div = await all_spans[2].query_selector('div')
                        if address_div:
                            info['registered_agent']['address'] = await address_div.inner_text()
            
            # Extract Authorized Person(s) - for LLCs
            auth_section = await page.query_selector('span:text("Authorized Person(s) Detail")')
            if auth_section:
                parent = await auth_section.evaluate_handle('(el) => el.parentElement')
                if parent:
                    text = await parent.inner_text()
                    lines = [l.strip() for l in text.splitlines() if l.strip()]
                    
                    current_person = {}
                    
                    for i, line in enumerate(lines):
                        if 'Authorized Person' in line or 'Name & Address' in line:
                            continue
                        
                        if line.startswith('Title'):
                            if current_person and 'full_name' in current_person:
                                info['authorized_persons'].append(current_person)
                            
                            line_clean = line.replace('\xa0', ' ')
                            title_parts = line_clean.split(None, 1)
                            if len(title_parts) > 1:
                                current_person = {'title': title_parts[1]}
                        
                        elif current_person and 'title' in current_person and 'full_name' not in current_person:
                            # Skip if this looks like an address line (using improved detection)
                            if self._is_likely_address_line(line):
                                continue
                            # Skip if line contains state abbreviation and zip
                            if re.search(r'\b[A-Z]{2}\s+\d{5}', line):
                                continue
                            # Skip if line is just numbers
                            if line.replace(' ', '').isdigit():
                                continue
                                
                            # This should be a name
                            if ',' in line:
                                parts = line.split(',', 1)
                                current_person['last_name'] = parts[0].strip()
                                current_person['first_name'] = parts[1].strip() if len(parts) > 1 else ''
                                current_person['full_name'] = line
                            elif line and len(line) > 2:
                                name_parts = line.split()
                                if len(name_parts) >= 2:
                                    current_person['first_name'] = name_parts[0]
                                    current_person['last_name'] = ' '.join(name_parts[1:])
                                else:
                                    current_person['first_name'] = ''
                                    current_person['last_name'] = line
                                current_person['full_name'] = line
                    
                    if current_person and 'full_name' in current_person:
                        info['authorized_persons'].append(current_person)
            
            # Extract Officer/Director Detail - for Corporations
            officer_section = await page.query_selector('span:text("Officer/Director Detail")')
            if officer_section:
                parent = await officer_section.evaluate_handle('(el) => el.parentElement')
                if parent:
                    text = await parent.inner_text()
                    lines = [l.strip() for l in text.splitlines() if l.strip()]
                    
                    current_officer = {}
                    
                    for i, line in enumerate(lines):
                        if 'Officer/Director' in line or 'Name & Address' in line:
                            continue
                        
                        if line.startswith('Title'):
                            if current_officer and 'full_name' in current_officer:
                                info['officers'].append(current_officer)
                            
                            line_clean = line.replace('\xa0', ' ')
                            title_parts = line_clean.split(None, 1)
                            if len(title_parts) > 1:
                                current_officer = {'title': title_parts[1]}
                            elif i + 1 < len(lines):
                                current_officer = {'title': lines[i + 1]}
                        
                        elif current_officer and 'title' in current_officer and 'full_name' not in current_officer:
                            # Skip if this is the title value we already captured
                            if line == current_officer.get('title'):
                                continue
                            # Skip if this looks like an address line (using improved detection)
                            if self._is_likely_address_line(line):
                                continue
                            # Skip if line contains state abbreviation and zip
                            if re.search(r'\b[A-Z]{2}\s+\d{5}', line):
                                continue
                            # Skip if line is just numbers
                            if line.replace(' ', '').isdigit():
                                continue
                                
                            # This should be a name
                            if ',' in line:
                                parts = line.split(',', 1)
                                current_officer['last_name'] = parts[0].strip()
                                current_officer['first_name'] = parts[1].strip() if len(parts) > 1 else ''
                                current_officer['full_name'] = line
                            elif line and len(line) > 2:
                                name_parts = line.split()
                                if len(name_parts) >= 2:
                                    current_officer['first_name'] = name_parts[0]
                                    current_officer['last_name'] = ' '.join(name_parts[1:])
                                else:
                                    current_officer['first_name'] = ''
                                    current_officer['last_name'] = line
                                current_officer['full_name'] = line
                    
                    if current_officer and 'full_name' in current_officer:
                        info['officers'].append(current_officer)
            
            # Combine officers and authorized persons for owner detection
            all_persons = info['officers'] + info['authorized_persons']
            
            logger.info(f"Extracted {len(info['officers'])} officers and {len(info['authorized_persons'])} authorized persons from Sunbiz")
            logger.info(f"Company filed on: {info['filing_info'].get('date_filed', 'Unknown')}")
            logger.info(f"FEIN: {info['filing_info'].get('fein', 'Not found')}")
            
        except Exception as e:
            logger.error(f"Error extracting corporate info: {e}")
        
        return info


# Test function
async def test_fixed_scraper():
    """Test the fixed Sunbiz scraper with TSAS INC."""
    scraper = SunbizScraperFixed()
    
    result = await scraper.search_business("TSAS INC")
    
    if result:
        print("\n=== TSAS INC - Fixed Scraper Results ===")
        print(f"Officers found: {len(result['officers'])}")
        for officer in result['officers']:
            print(f"  - {officer.get('full_name', 'Unknown')} (Title: {officer.get('title', 'Unknown')})")
        
        print(f"\nAuthorized Persons: {len(result.get('authorized_persons', []))}")
        for person in result.get('authorized_persons', []):
            print(f"  - {person.get('full_name')} ({person.get('title')})")
        
        if result['registered_agent']:
            print(f"\nRegistered Agent: {result['registered_agent'].get('name', 'Unknown')}")
    else:
        print("No results found")
    
    return result


if __name__ == "__main__":
    # Test the fixed scraper
    asyncio.run(test_fixed_scraper())