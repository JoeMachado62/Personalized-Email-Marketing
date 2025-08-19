#!/usr/bin/env python3
"""
Enhanced Sunbiz matcher with advanced fuzzy matching and entity type flexibility.
This version handles quotes, entity type variations, and DBA names.
"""

import asyncio
import logging
import re
from typing import Dict, Any, Optional, List, Tuple
from patch_sunbiz_scraper import SunbizScraperFixed

logger = logging.getLogger(__name__)


class EnhancedSunbizMatcher(SunbizScraperFixed):
    """
    Enhanced version with better matching logic for edge cases.
    """
    
    def __init__(self):
        super().__init__()
        
        # Entity type equivalences
        self.entity_equivalences = {
            'LLC': ['LLC', 'L.L.C.', 'L.L.C', 'LIMITED LIABILITY COMPANY', 'LIMITED LIABILITY CO'],
            'INC': ['INC', 'INC.', 'INCORPORATED', 'INCORPORATION'],
            'CORP': ['CORP', 'CORP.', 'CORPORATION'],
            'CO': ['CO', 'CO.', 'COMPANY'],
            'LTD': ['LTD', 'LTD.', 'LIMITED'],
            'PA': ['PA', 'P.A.', 'PROFESSIONAL ASSOCIATION'],
            'PC': ['PC', 'P.C.', 'PROFESSIONAL CORPORATION'],
            'PLLC': ['PLLC', 'P.L.L.C.', 'PROFESSIONAL LIMITED LIABILITY COMPANY'],
            'LP': ['LP', 'L.P.', 'LIMITED PARTNERSHIP'],
            'LLP': ['LLP', 'L.L.P.', 'LIMITED LIABILITY PARTNERSHIP'],
            'LLLP': ['LLLP', 'L.L.L.P.', 'LIMITED LIABILITY LIMITED PARTNERSHIP']
        }
        
        # Create reverse mapping
        self.entity_map = {}
        for canonical, variants in self.entity_equivalences.items():
            for variant in variants:
                self.entity_map[variant.upper()] = canonical
    
    def extract_entity_type(self, name: str) -> Tuple[str, str]:
        """
        Extract the entity type from a company name.
        Returns (name_without_entity, entity_type)
        """
        name_upper = name.upper().strip()
        
        # Sort by length descending to match longer variants first
        all_variants = []
        for variants in self.entity_equivalences.values():
            all_variants.extend(variants)
        all_variants.sort(key=len, reverse=True)
        
        for variant in all_variants:
            # Check if name ends with this variant
            pattern = r'\b' + re.escape(variant) + r'\s*$'
            if re.search(pattern, name_upper):
                # Remove the entity type
                name_without = re.sub(pattern, '', name_upper).strip()
                # Remove trailing commas
                name_without = name_without.rstrip(',').strip()
                canonical = self.entity_map.get(variant.upper(), variant)
                return name_without, canonical
        
        return name_upper, None
    
    def normalize_for_comparison(self, text: str) -> str:
        """
        Enhanced normalization that handles quotes and special cases.
        """
        if not text:
            return ""
        
        text = text.upper()
        
        # Remove quotes around entity types (handles "LLC" case)
        text = re.sub(r'"([A-Z\.]+)"', r'\1', text)
        
        # Remove all quotes
        text = text.replace('"', '').replace("'", '')
        
        # Handle DBA - extract primary name
        if ' DBA ' in text or ' D/B/A ' in text or ' D.B.A' in text:
            text = re.split(r'\s+D/?B/?A?\s+', text)[0]
        
        # Remove common punctuation
        text = re.sub(r'[,.\-&/()]', ' ', text)
        
        # Normalize spaces
        text = ' '.join(text.split())
        
        return text
    
    def calculate_match_score(self, search_name: str, result_name: str) -> float:
        """
        Calculate sophisticated match score considering entity type flexibility.
        """
        # First, try simple normalization
        search_norm = self.normalize_for_comparison(search_name)
        result_norm = self.normalize_for_comparison(result_name)
        
        # Exact match after normalization
        if search_norm == result_norm:
            return 1.0
        
        # Extract entity types
        search_base, search_entity = self.extract_entity_type(search_norm)
        result_base, result_entity = self.extract_entity_type(result_norm)
        
        # If base names match exactly, high score even if entity types differ
        if search_base == result_base:
            if search_entity == result_entity:
                return 0.99  # Near perfect
            else:
                return 0.85  # Base match, different entity type
        
        # Remove spaces for comparison (handles J D vs JD)
        search_no_space = search_base.replace(' ', '')
        result_no_space = result_base.replace(' ', '')
        
        if search_no_space == result_no_space:
            if search_entity == result_entity:
                return 0.95
            else:
                return 0.80
        
        # Token-based matching
        search_tokens = set(search_base.split())
        result_tokens = set(result_base.split())
        
        if search_tokens and result_tokens:
            intersection = search_tokens & result_tokens
            union = search_tokens | result_tokens
            jaccard = len(intersection) / len(union)
            
            # Bonus if all search tokens are in result
            if search_tokens.issubset(result_tokens):
                jaccard += 0.1
            
            # Consider entity type match
            if search_entity and result_entity:
                if search_entity == result_entity:
                    jaccard += 0.05
            
            return min(jaccard, 0.99)
        
        return 0.0
    
    async def search_business_enhanced(self, business_name: str) -> Optional[Dict[str, Any]]:
        """
        Enhanced search that tries multiple strategies.
        """
        # First, try the original search
        result = await self.search_business(business_name)
        if result:
            return result
        
        # If no result, try alternative strategies
        logger.info(f"No direct match for {business_name}, trying alternatives...")
        
        # Strategy 1: Remove DBA portion if present
        if ' DBA ' in business_name.upper():
            primary_name = business_name.split(' DBA ')[0].strip()
            logger.info(f"Trying primary name: {primary_name}")
            result = await self.search_business(primary_name)
            if result:
                return result
        
        # Strategy 2: Try different entity types
        base_name, entity_type = self.extract_entity_type(business_name)
        if entity_type:
            # Try common alternatives
            alternatives = []
            if entity_type == 'LLC':
                alternatives = ['INC', 'CORP', 'INCORPORATED']
            elif entity_type == 'INC':
                alternatives = ['LLC', 'CORP']
            elif entity_type == 'CORP':
                alternatives = ['INC', 'LLC']
            
            for alt in alternatives:
                alt_name = f"{base_name} {alt}"
                logger.info(f"Trying alternative entity: {alt_name}")
                result = await self.search_business(alt_name)
                if result:
                    logger.info(f"Found with alternative entity type: {alt}")
                    return result
        
        # Strategy 3: Try without entity type
        if entity_type:
            logger.info(f"Trying without entity type: {base_name}")
            result = await self.search_business(base_name)
            if result:
                return result
        
        return None
    
    async def search_business(self, business_name: str) -> Optional[Dict[str, Any]]:
        """
        Override to use enhanced matching logic.
        """
        try:
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
                )
                
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    viewport={'width': 1920, 'height': 1080}
                )
                
                page = await context.new_page()
                
                logger.info(f"Searching Sunbiz for: {business_name}")
                await page.goto(self.search_url, wait_until='domcontentloaded')
                await page.wait_for_timeout(1000)
                
                search_input = await page.wait_for_selector('input[name="SearchTerm"]', timeout=5000)
                await search_input.click()
                await page.wait_for_timeout(500)
                await search_input.type(business_name, delay=50)
                await page.wait_for_timeout(500)
                
                search_button = await page.query_selector('input[type="submit"][value="Search Now"]')
                if search_button:
                    await search_button.click()
                else:
                    await page.press('input[name="SearchTerm"]', 'Enter')
                
                await page.wait_for_load_state('networkidle', timeout=10000)
                
                result_links = await page.query_selector_all('a[href*="SearchResultDetail"]')
                
                if not result_links:
                    logger.warning(f"No results found for: {business_name}")
                    await browser.close()
                    return None
                
                logger.info(f"Found {len(result_links)} potential matches")
                
                # Score all results
                scored_results = []
                for link in result_links:
                    name_text = await link.inner_text()
                    score = self.calculate_match_score(business_name, name_text)
                    scored_results.append((score, name_text, link))
                    
                    if score >= 0.95:  # Very high confidence
                        logger.info(f"High confidence match (score={score:.2f}): {name_text}")
                        await link.click()
                        await page.wait_for_load_state('networkidle')
                        result = await self._extract_corporate_info(page)
                        await browser.close()
                        return result
                
                # Sort by score
                scored_results.sort(reverse=True)
                
                # Take best match if score is reasonable
                if scored_results and scored_results[0][0] >= 0.75:
                    best_score, best_name, best_link = scored_results[0]
                    logger.info(f"Best match (score={best_score:.2f}): {best_name}")
                    await best_link.click()
                    await page.wait_for_load_state('networkidle')
                    result = await self._extract_corporate_info(page)
                    await browser.close()
                    return result
                
                logger.warning(f"No sufficient match found for: {business_name}")
                logger.warning(f"Best score was {scored_results[0][0]:.2f} for {scored_results[0][1]}" if scored_results else "No scores")
                
                await browser.close()
                return None
                
        except Exception as e:
            logger.error(f"Error in enhanced search for {business_name}: {e}")
            return None


# Test function
async def test_enhanced_matcher():
    """Test the enhanced matcher with problematic cases."""
    
    matcher = EnhancedSunbizMatcher()
    
    test_cases = [
        "G & G SALES AND SERVICE LLC",  # Has quotes in Sunbiz
        "DEAL MAKER OF GAINESVILLE LLC",  # Listed as LIMITED LIABILITY COMPANY
        "FAST FREDDY'S AUTO SALES LLC",  # Has quotes
        "GAMAS CORP DBA GAMAS AUTO SALES",  # DBA name
    ]
    
    for company in test_cases:
        print(f"\nTesting: {company}")
        result = await matcher.search_business_enhanced(company)
        
        if result:
            print(f"✓ FOUND: {result.get('company_name')}")
            officers = result.get('officers', [])
            auth = result.get('authorized_persons', [])
            if officers:
                print(f"  Owner: {officers[0].get('full_name')} ({officers[0].get('title')})")
            elif auth:
                print(f"  Owner: {auth[0].get('full_name')} ({auth[0].get('title')})")
        else:
            print(f"✗ NOT FOUND")
    
    return


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_enhanced_matcher())