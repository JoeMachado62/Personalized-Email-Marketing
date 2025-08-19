#!/usr/bin/env python3
"""
Multi-URL Scraper V2 - Enhanced parallel scraping with Playwright.

This refactored scraper integrates with the new PersonalizationIntelligence
architecture and uses Playwright for robust multi-source data collection.

Key improvements:
- Playwright-based parallel scraping
- Integration with PersonalizationIntelligence
- Better categorization and prioritization
- Improved business registry handling
- Optimized for enrichment accuracy
"""

import asyncio
import logging
import re
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from urllib.parse import urlparse, urljoin
import trafilatura
from bs4 import BeautifulSoup

from .intelligent_extractor_v2 import (
    PersonalizationIntelligence,
    PlaywrightStealthBrowser
)
from .unified_web_scraper import UnifiedWebScraper

logger = logging.getLogger(__name__)


class MultiURLScraperV2:
    """
    Production-ready multi-URL scraper optimized for comprehensive data extraction.
    """
    
    # Source categorization with priorities
    SOURCE_PRIORITIES = {
        'business_registry': {
            'patterns': ['sunbiz', 'sos.state', 'corporations', 'dos.myflorida'],
            'weight': 100,  # Highest priority
            'max_urls': 3
        },
        'company_website': {
            'weight': 90,
            'max_urls': 2
        },
        'major_directories': {
            'patterns': ['yelp.com', 'yellowpages.com', 'bbb.org'],
            'weight': 70,
            'max_urls': 3
        },
        'social_media': {
            'patterns': ['facebook.com', 'linkedin.com', 'twitter.com', 'instagram.com'],
            'weight': 60,
            'max_urls': 2
        },
        'review_sites': {
            'patterns': ['google.com/maps', 'yelp.com/biz', 'trustpilot'],
            'weight': 50,
            'max_urls': 2
        },
        'news_articles': {
            'patterns': ['news', 'press', 'article', 'blog'],
            'weight': 40,
            'max_urls': 2
        }
    }
    
    def __init__(
        self,
        max_urls: int = 12,
        parallel_limit: int = 3,
        use_stealth: bool = True
    ):
        """
        Initialize the multi-URL scraper.
        
        Args:
            max_urls: Maximum URLs to scrape per company
            parallel_limit: Number of URLs to scrape in parallel
            use_stealth: Use stealth browsing techniques
        """
        self.max_urls = max_urls
        self.parallel_limit = parallel_limit
        self.use_stealth = use_stealth
        self.unified_scraper = UnifiedWebScraper(use_stealth=use_stealth)
        self.visited_urls: Set[str] = set()
    
    async def scrape_multiple_sources(
        self,
        company_name: str,
        search_results: List[Dict],
        location: Optional[str] = None,
        campaign_context: Optional[Dict] = None
    ) -> PersonalizationIntelligence:
        """
        Main method to scrape multiple sources and build PersonalizationIntelligence.
        
        Args:
            company_name: Name of the company
            search_results: Search results to process
            location: Optional location information
            campaign_context: Campaign context for targeted extraction
            
        Returns:
            Comprehensive PersonalizationIntelligence
        """
        logger.info(f"Starting multi-source scraping for {company_name}")
        
        # Initialize intelligence
        intelligence = PersonalizationIntelligence(
            business_name=company_name
        )
        
        try:
            # Step 1: Categorize search results
            categorized = self._categorize_sources(search_results, company_name)
            
            # Step 2: Extract company website URL if found
            if categorized.get('company_website'):
                # Take the first company website as the primary website
                website_url = categorized['company_website'][0].get('link', categorized['company_website'][0].get('url', ''))
                if website_url:
                    intelligence.website_url = website_url
                    logger.info(f"Found company website: {website_url}")
            
            # Step 3: Select best URLs to scrape
            urls_to_scrape = self._prioritize_urls(categorized)
            logger.info(f"Selected {len(urls_to_scrape)} URLs to scrape")
            
            # Step 3: Initialize Playwright browser
            await self.unified_scraper.initialize()
            
            # Step 4: Scrape URLs in parallel batches
            all_extracted_data = await self._parallel_extract(urls_to_scrape)
            
            # Step 5: Process extracted data by source type
            await self._process_by_source_type(all_extracted_data, intelligence)
            
            # Step 6: Cross-reference and validate data
            self._cross_reference_data(intelligence)
            
            # Step 7: Generate personalization elements
            self._generate_personalization_elements(intelligence)
            
            # Step 8: Calculate confidence
            intelligence.extraction_confidence = self._calculate_confidence(
                intelligence,
                len(all_extracted_data)
            )
            
            # Step 9: Assess data freshness
            intelligence.data_freshness = self._assess_freshness(all_extracted_data)
            
            logger.info(
                f"Completed multi-source scraping: {len(all_extracted_data)} sources, "
                f"confidence: {intelligence.extraction_confidence:.1%}"
            )
            
        except Exception as e:
            logger.error(f"Multi-source scraping error: {e}")
            intelligence.website_issues.append(f"Extraction error: {str(e)}")
        
        return intelligence
    
    def _categorize_sources(
        self,
        search_results: List[Dict],
        company_name: str
    ) -> Dict[str, List[Dict]]:
        """Categorize search results by type and relevance."""
        
        categorized = {
            'business_registry': [],
            'company_website': [],
            'major_directories': [],
            'social_media': [],
            'review_sites': [],
            'news_articles': [],
            'other': []
        }
        
        company_words = set(company_name.lower().split())
        
        for result in search_results:
            url = result.get('link', result.get('url', ''))
            title = result.get('title', '').lower()
            snippet = result.get('snippet', '').lower()
            
            if not url or url in self.visited_urls:
                continue
            
            domain = urlparse(url).netloc.lower()
            
            # Business registries (highest priority)
            if any(pattern in domain for pattern in self.SOURCE_PRIORITIES['business_registry']['patterns']):
                categorized['business_registry'].append(result)
                continue
            
            # Company website (check domain match)
            # Exclude obviously wrong domains (financial, government, etc.)
            excluded_domains = ['yelp', 'facebook', 'linkedin', 'yellowpages', 'bbb.org', 
                              'sec.gov', 'edgar', 'blueowl', 'capital', 'investment', 
                              '.gov', 'wikipedia', 'bloomberg', 'reuters']
            
            if any(excluded in domain for excluded in excluded_domains):
                # Skip these - not company websites
                pass
            else:
                # Check if domain contains significant company words
                domain_match = sum(1 for word in company_words if word in domain and len(word) > 3)
                # Also check title/snippet for company name
                content_match = sum(1 for word in company_words if word in title and len(word) > 3)
                
                # Need stronger match to be considered company website
                if (domain_match >= 1 and content_match >= 1) or domain_match >= 2:
                    categorized['company_website'].append(result)
                    continue
            
            # Social media
            if any(pattern in domain for pattern in self.SOURCE_PRIORITIES['social_media']['patterns']):
                if any(word in title + snippet for word in company_words):
                    categorized['social_media'].append(result)
                continue
            
            # Major directories
            if any(pattern in domain for pattern in self.SOURCE_PRIORITIES['major_directories']['patterns']):
                categorized['major_directories'].append(result)
                continue
            
            # Review sites
            if any(pattern in url.lower() for pattern in self.SOURCE_PRIORITIES['review_sites']['patterns']):
                categorized['review_sites'].append(result)
                continue
            
            # News articles
            if any(pattern in domain for pattern in self.SOURCE_PRIORITIES['news_articles']['patterns']):
                if any(word in title + snippet for word in company_words):
                    categorized['news_articles'].append(result)
                continue
            
            # Other relevant results
            relevance = sum(1 for word in company_words if word in title + snippet)
            if relevance >= 2:
                categorized['other'].append(result)
        
        # Log categorization
        for category, items in categorized.items():
            if items:
                logger.info(f"  {category}: {len(items)} results")
        
        return categorized
    
    def _prioritize_urls(self, categorized: Dict[str, List[Dict]]) -> List[Dict]:
        """Select and prioritize URLs to scrape based on value."""
        
        prioritized = []
        
        # Process each category by priority
        for category, config in self.SOURCE_PRIORITIES.items():
            if category in categorized:
                urls = categorized[category][:config.get('max_urls', 2)]
                for url_data in urls:
                    url_data['category'] = category
                    url_data['priority'] = config['weight']
                    prioritized.append(url_data)
        
        # Add some "other" URLs if we have room
        remaining_slots = self.max_urls - len(prioritized)
        if remaining_slots > 0 and 'other' in categorized:
            for url_data in categorized['other'][:remaining_slots]:
                url_data['category'] = 'other'
                url_data['priority'] = 30
                prioritized.append(url_data)
        
        # Sort by priority
        prioritized.sort(key=lambda x: x['priority'], reverse=True)
        
        return prioritized[:self.max_urls]
    
    async def _parallel_extract(self, urls_to_scrape: List[Dict]) -> List[Dict]:
        """Extract data from multiple URLs in parallel."""
        
        all_data = []
        
        # Process in batches
        for i in range(0, len(urls_to_scrape), self.parallel_limit):
            batch = urls_to_scrape[i:i + self.parallel_limit]
            
            # Create extraction tasks
            tasks = []
            for url_data in batch:
                url = url_data.get('link', url_data.get('url', ''))
                if url:
                    tasks.append(self._extract_single_source(url, url_data))
            
            # Execute batch
            if tasks:
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in batch_results:
                    if isinstance(result, Exception):
                        logger.warning(f"Extraction error: {result}")
                    elif result:
                        all_data.append(result)
                        self.visited_urls.add(result['url'])
                
                # Delay between batches
                if i + self.parallel_limit < len(urls_to_scrape):
                    await asyncio.sleep(1)
        
        return all_data
    
    async def _extract_single_source(self, url: str, url_data: Dict) -> Dict:
        """Extract data from a single source with improved extraction for dynamic sites."""
        
        result = {
            'url': url,
            'category': url_data.get('category', 'other'),
            'title': url_data.get('title', ''),
            'snippet': url_data.get('snippet', ''),
            'extracted_data': {},
            'raw_text': '',
            'extraction_time': datetime.now().isoformat()
        }
        
        try:
            # Determine extraction method based on site type
            if result['category'] == 'business_registry':
                # Use direct Playwright extraction for dynamic registry sites
                extracted_text = await self._extract_dynamic_content(url)
                if extracted_text:
                    result['raw_text'] = extracted_text
                    result['is_registry'] = True
                    result['registry_data'] = self._parse_business_registry(
                        extracted_text,
                        url
                    )
                    logger.info(f"Extracted {len(extracted_text)} chars from registry {urlparse(url).netloc}")
                else:
                    logger.warning(f"Failed to extract dynamic content from {url}")
            else:
                # Use unified scraper for regular sites
                scrape_result = await self.unified_scraper.scrape_url(url)
                
                if scrape_result['success']:
                    content = scrape_result.get('content', {})
                    
                    # Store raw text
                    if isinstance(content, dict):
                        result['raw_text'] = content.get('text', '')
                        result['extracted_data'] = content
                    else:
                        result['raw_text'] = str(content)
                    
                    logger.info(f"Extracted {len(result['raw_text'])} chars from {urlparse(url).netloc}")
                else:
                    logger.warning(f"Failed to extract from {url}: {scrape_result.get('error')}")
                
        except Exception as e:
            logger.error(f"Error extracting {url}: {e}")
            result['error'] = str(e)
        
        return result
    
    async def _extract_dynamic_content(self, url: str) -> str:
        """
        Universal extraction method for dynamic/structured sites.
        Uses Playwright to get all visible text, handling JavaScript-rendered content.
        """
        try:
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0"
                )
                page = await context.new_page()
                
                # Navigate to the page
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                
                # Wait for dynamic content to load
                await page.wait_for_timeout(3000)
                
                # Try to wait for common loading indicators to disappear
                loading_selectors = ['.loading', '.spinner', '#loading']
                for selector in loading_selectors:
                    try:
                        await page.wait_for_selector(selector, state='hidden', timeout=1000)
                    except:
                        pass  # Selector not found or already hidden
                
                # Extract all visible text using multiple strategies
                extracted_text = ""
                
                # Strategy 1: Get innerText of body (preserves layout)
                try:
                    body_text = await page.inner_text('body')
                    extracted_text = body_text
                except:
                    pass
                
                # Strategy 2: If body text is too short, try getting all text nodes
                if len(extracted_text) < 500:
                    try:
                        all_text = await page.evaluate("""
                            () => {
                                const walker = document.createTreeWalker(
                                    document.body,
                                    NodeFilter.SHOW_TEXT,
                                    {
                                        acceptNode: function(node) {
                                            const parent = node.parentElement;
                                            if (parent && (
                                                parent.tagName === 'SCRIPT' || 
                                                parent.tagName === 'STYLE' ||
                                                parent.tagName === 'NOSCRIPT'
                                            )) {
                                                return NodeFilter.FILTER_REJECT;
                                            }
                                            if (node.nodeValue && node.nodeValue.trim().length > 0) {
                                                return NodeFilter.FILTER_ACCEPT;
                                            }
                                            return NodeFilter.FILTER_REJECT;
                                        }
                                    }
                                );
                                
                                let text = [];
                                let node;
                                while (node = walker.nextNode()) {
                                    text.push(node.nodeValue.trim());
                                }
                                return text.join('\\n');
                            }
                        """)
                        if len(all_text) > len(extracted_text):
                            extracted_text = all_text
                    except:
                        pass
                
                # Strategy 3: For specific structured sites, look for data sections
                if 'sunbiz' in url.lower():
                    # Extract detail sections specifically
                    try:
                        sections = await page.query_selector_all('.detailSection')
                        section_texts = []
                        for section in sections:
                            section_text = await section.inner_text()
                            section_texts.append(section_text)
                        if section_texts:
                            extracted_text = '\n\n'.join(section_texts)
                    except:
                        pass
                
                await browser.close()
                return extracted_text
                
        except Exception as e:
            logger.error(f"Error extracting dynamic content from {url}: {e}")
            return ""
    
    def _parse_business_registry(self, text: str, url: str) -> Dict:
        """Parse business registry data for owner information - works universally."""
        
        registry_data = {
            'owner_name': '',
            'owner_title': '',
            'officers': [],
            'registered_agent': '',
            'status': '',
            'filing_date': '',
            'website': ''  # Add website field
        }
        
        # Universal patterns that work across different registry sites
        
        # Extract website if present
        website_patterns = [
            r'Website[:\s]*([^\s<>"]+)',
            r'Web[:\s]*([^\s<>"]+)',
            r'URL[:\s]*([^\s<>"]+)',
            r'Internet Address[:\s]*([^\s<>"]+)',
            r'www\.[^\s<>"]+',
            r'https?://[^\s<>"]+'
        ]
        
        for pattern in website_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                website = match.group(1) if match.groups() else match.group(0)
                website = website.strip().rstrip('.,)')
                # Add protocol if missing
                if not website.startswith('http'):
                    website = 'https://' + website if website.startswith('www.') else 'https://www.' + website
                registry_data['website'] = website
                break
        
        # Pattern 1: Look for "Title [TITLE]" followed by name on next line
        title_name_pattern = r'Title\s+([A-Z]+(?:\s+[A-Z]+)?)\s*\n\s*([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)'
        matches = re.findall(title_name_pattern, text)
        for title, name in matches:
            if len(name.split()) >= 2 and not registry_data['owner_name']:
                registry_data['owner_name'] = name
                registry_data['owner_title'] = title.title()
                registry_data['officers'].append({'name': name, 'title': title.title()})
        
        # Pattern 2: Look for authorized person sections
        auth_pattern = r'Authorized Person(?:s)?\s+Detail[^\n]*\n(?:[^\n]*\n)*?Title\s+(\w+)\s*\n\s*([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)'
        matches = re.findall(auth_pattern, text, re.IGNORECASE)
        for title, name in matches:
            if len(name.split()) >= 2 and not registry_data['owner_name']:
                registry_data['owner_name'] = name
                registry_data['owner_title'] = title.title()
                registry_data['officers'].append({'name': name, 'title': title.title()})
        
        # Pattern 3: Officer/Director patterns
        officer_patterns = [
            r'(?:President|CEO|Manager|Member|Director|Owner|Vice President|Secretary|Treasurer)\s*[:\s]\s*([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)+)',
            r'([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)+)\s*[,-]\s*(?:President|CEO|Manager|Owner|Director)',
            r'Name\s*[:\s]\s*([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)+)\s*Title\s*[:\s]\s*(\w+)'
        ]
        
        for pattern in officer_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                if len(match.groups()) == 2:  # Name and title
                    name = match.group(1).strip()
                    title = match.group(2).strip()
                else:
                    name = match.group(1).strip()
                    # Extract title from context
                    if 'President' in match.group(0):
                        title = 'President'
                    elif 'CEO' in match.group(0):
                        title = 'CEO'
                    elif 'Manager' in match.group(0):
                        title = 'Manager'
                    elif 'Director' in match.group(0):
                        title = 'Director'
                    elif 'Owner' in match.group(0):
                        title = 'Owner'
                    else:
                        title = 'Officer'
                
                if len(name.split()) >= 2:  # Ensure it's a full name
                    if not registry_data['owner_name']:
                        registry_data['owner_name'] = name
                        registry_data['owner_title'] = title
                    registry_data['officers'].append({'name': name, 'title': title})
        
        # Registered Agent - universal pattern
        agent_pattern = r'Registered Agent[:\s]+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)'
        agent_match = re.search(agent_pattern, text)
        if agent_match:
            registry_data['registered_agent'] = agent_match.group(1).strip()
        
        # Status - universal pattern
        status_pattern = r'Status[:\s]+(Active|Inactive|Dissolved|Good Standing)'
        status_match = re.search(status_pattern, text, re.IGNORECASE)
        if status_match:
            registry_data['status'] = status_match.group(1)
        
        # Filing date - multiple patterns for different formats
        date_patterns = [
            r'(?:File|Filed|Filing)\s+Date[:\s]+(\d{1,2}/\d{1,2}/\d{4})',
            r'Date\s+(?:Filed|Formed|Incorporated)[:\s]+(\d{1,2}/\d{1,2}/\d{4})',
            r'(?:Incorporated|Formed|Established)[:\s]+(\d{1,2}/\d{1,2}/\d{4})'
        ]
        for pattern in date_patterns:
            date_match = re.search(pattern, text, re.IGNORECASE)
            if date_match:
                registry_data['filing_date'] = date_match.group(1)
                break
        
        return registry_data
    
    async def _process_by_source_type(
        self,
        all_data: List[Dict],
        intelligence: PersonalizationIntelligence
    ):
        """Process extracted data by source type."""
        
        for data in all_data:
            category = data.get('category')
            text = data.get('raw_text', '')
            
            if not text:
                continue
            
            # Add to sources analyzed
            intelligence.sources_analyzed.append(data['url'])
            
            # Process based on category
            if category == 'business_registry':
                self._process_registry_data(data, intelligence)
            
            elif category == 'company_website':
                self._process_website_data(text, intelligence)
            
            elif category == 'major_directories':
                self._process_directory_data(text, intelligence)
            
            elif category == 'social_media':
                self._process_social_data(text, data['url'], intelligence)
            
            elif category == 'review_sites':
                self._process_review_data(text, intelligence)
            
            elif category == 'news_articles':
                self._process_news_data(text, data, intelligence)
            
            # Always extract these high-value elements
            self._extract_contact_info(text, intelligence)
            self._extract_achievements(text, intelligence)
            self._identify_pain_points(text, data['url'], intelligence)
    
    def _process_registry_data(self, data: Dict, intelligence: PersonalizationIntelligence):
        """Process business registry data."""
        
        registry = data.get('registry_data', {})
        
        if registry.get('owner_name'):
            intelligence.owner_name = registry['owner_name']
            intelligence.owner_title = registry.get('owner_title', '')
            
            # Add to decision makers
            intelligence.key_decision_makers.append({
                'name': registry['owner_name'],
                'title': registry.get('owner_title', 'Owner'),
                'source': 'business_registry'
            })
        
        # Add all officers
        for officer in registry.get('officers', []):
            intelligence.key_decision_makers.append({
                'name': officer.get('name', ''),
                'title': officer.get('title', 'Officer'),
                'source': 'business_registry'
            })
        
        # Business status
        if registry.get('status'):
            status = registry['status']
            if 'Active' in status or 'Good Standing' in status:
                intelligence.certifications.append(f"Business Status: {status}")
                intelligence.recent_wins.append(f"Maintained {status} status")
        
        # Years in business - VERY IMPORTANT for personalization
        if registry.get('filing_date'):
            try:
                # Parse date - handle MM/DD/YYYY format
                parts = registry['filing_date'].split('/')
                if len(parts) == 3:
                    filing_year = int(parts[2])
                    years = datetime.now().year - filing_year
                    intelligence.years_in_business = years
                    
                    # Add as an achievement if significant
                    if years >= 10:
                        intelligence.recent_wins.append(f"Established {years} years ago")
                        if years >= 25:
                            intelligence.recent_wins.append(f"Quarter-century of service")
                        elif years >= 50:
                            intelligence.recent_wins.append(f"Half-century in business")
            except Exception as e:
                logger.debug(f"Could not parse filing date: {registry['filing_date']}")
    
    def _process_website_data(self, text: str, intelligence: PersonalizationIntelligence):
        """Process company website data."""
        
        # Extract services
        service_patterns = [
            r'(?:we offer|our services|we provide)[:\s]+([^.]+)',
            r'(?:services|solutions)[:\s]+([^.]+)'
        ]
        
        for pattern in service_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                services_text = match.group(1)
                # Split and clean
                services = [s.strip() for s in re.split(r'[,;•|]', services_text)]
                intelligence.primary_services.extend(
                    [s for s in services if 10 < len(s) < 50]
                )
        
        # Extract values
        value_patterns = [
            r'(?:our mission|we believe|committed to)[:\s]+([^.]{20,150})',
            r'(?:our values|core values)[:\s]+([^.]{20,200})'
        ]
        
        for pattern in value_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                intelligence.company_values.append(match.group(1).strip())
        
        # Check for missing capabilities
        if 'book online' not in text.lower() and 'schedule online' not in text.lower():
            intelligence.missing_capabilities.append("No online booking")
        
        if 'shop online' not in text.lower() and 'buy online' not in text.lower():
            intelligence.missing_capabilities.append("No e-commerce")
    
    def _process_directory_data(self, text: str, intelligence: PersonalizationIntelligence):
        """Process business directory data."""
        
        # Extract website from directory listings if not already found
        if not intelligence.website_url:
            website = self._extract_website_from_text(text)
            if website:
                intelligence.website_url = website
                logger.info(f"Found website in directory: {website}")
        
        # Business hours
        hours_pattern = r'(?:hours?|open)[:\s]*([0-9]{1,2}(?::[0-9]{2})?\s*[ap]m\s*-\s*[0-9]{1,2}(?::[0-9]{2})?\s*[ap]m)'
        hours = re.findall(hours_pattern, text, re.IGNORECASE)
        if hours and not intelligence.business_philosophy:
            intelligence.business_philosophy = f"Open {hours[0]}"
        
        # Specializations
        if 'dealer' in text.lower():
            specs = []
            for spec in ['new cars', 'used cars', 'trucks', 'suvs', 'luxury', 'commercial']:
                if spec in text.lower():
                    specs.append(spec.title())
            if specs:
                intelligence.unique_value_props.extend(specs[:3])
    
    def _process_social_data(
        self,
        text: str,
        url: str,
        intelligence: PersonalizationIntelligence
    ):
        """Process social media data."""
        
        # Extract social handle
        domain = urlparse(url).netloc.lower()
        path = urlparse(url).path
        
        if 'facebook' in domain:
            intelligence.social_media_profiles['facebook'] = url
        elif 'linkedin' in domain:
            intelligence.social_media_profiles['linkedin'] = url
        elif 'twitter' in domain or 'x.com' in domain:
            intelligence.social_media_profiles['twitter'] = url
        elif 'instagram' in domain:
            intelligence.social_media_profiles['instagram'] = url
        
        # Look for recent posts (simplified)
        if 'hours ago' in text or 'days ago' in text or 'yesterday' in text:
            intelligence.engagement_level = "High"
            intelligence.content_frequency = "Active"
        else:
            intelligence.engagement_level = "Medium"
            intelligence.content_frequency = "Moderate"
        
        # Extract recent social posts
        post_pattern = r'(?:posted|shared|announced)[:\s]+([^.]{20,100})'
        posts = re.findall(post_pattern, text, re.IGNORECASE)
        for post in posts[:3]:
            intelligence.latest_social_posts.append({
                'platform': domain.split('.')[0],
                'content': post.strip(),
                'source': url
            })
    
    def _process_review_data(self, text: str, intelligence: PersonalizationIntelligence):
        """Process review site data."""
        
        # Extract ratings
        rating_pattern = r'(\d(?:\.\d)?)\s*(?:out of\s*5|stars?|★)'
        ratings = re.findall(rating_pattern, text)
        
        if ratings:
            avg_rating = sum(float(r) for r in ratings if float(r) <= 5) / len(ratings)
            intelligence.ratings_summary = {
                'average': round(avg_rating, 1),
                'count': len(ratings),
                'source': 'aggregated'
            }
        
        # Extract positive testimonials
        quote_pattern = r'"([^"]{30,200})"'
        quotes = re.findall(quote_pattern, text)
        
        positive_words = ['great', 'excellent', 'best', 'recommend', 'amazing']
        for quote in quotes[:3]:
            if any(word in quote.lower() for word in positive_words):
                intelligence.customer_success_stories.append({
                    'text': quote,
                    'sentiment': 'positive',
                    'source': 'reviews'
                })
    
    def _process_news_data(self, text: str, data: Dict, intelligence: PersonalizationIntelligence):
        """Process news article data."""
        
        # Extract announcement title and date
        title = data.get('title', '')
        
        # Look for dates
        date_pattern = r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}'
        date_match = re.search(date_pattern, text)
        
        if title and date_match:
            intelligence.recent_announcements.append({
                'title': title,
                'date': date_match.group(0),
                'source': data['url']
            })
        
        # Look for achievements mentioned
        achievement_patterns = [
            r'(?:awarded|won|received)\s+([^.]{15,100})',
            r'(?:recognized|honored)\s+(?:as|for)\s+([^.]{15,100})'
        ]
        
        for pattern in achievement_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            intelligence.recent_wins.extend(matches[:2])
    
    def _extract_contact_info(self, text: str, intelligence: PersonalizationIntelligence):
        """Extract contact information."""
        
        # Phone
        if not intelligence.owner_phone:
            phone_pattern = r'(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
            phones = re.findall(phone_pattern, text)
            if phones:
                intelligence.owner_phone = phones[0]
        
        # Email
        if not intelligence.owner_email:
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = re.findall(email_pattern, text)
            
            # Prefer personal emails
            for email in emails:
                if not any(generic in email.lower() for generic in
                          ['info@', 'contact@', 'sales@', 'support@', 'noreply@']):
                    intelligence.owner_email = email
                    break
    
    def _extract_website_from_text(self, text: str) -> Optional[str]:
        """Extract website URL from text."""
        import re
        
        # Look for URLs in the text
        url_patterns = [
            r'https?://[^\s<>"]+',
            r'www\.[^\s<>"]+',
            r'Website:\s*([^\s<>"]+)',
            r'Web:\s*([^\s<>"]+)'
        ]
        
        for pattern in url_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                url = match.group(1) if match.groups() else match.group(0)
                # Clean up the URL
                url = url.strip().rstrip('.,)')
                # Add protocol if missing
                if not url.startswith('http'):
                    url = 'https://' + url if url.startswith('www.') else 'https://www.' + url
                return url
        
        return None
    
    def _extract_achievements(self, text: str, intelligence: PersonalizationIntelligence):
        """Extract achievements and awards."""
        
        patterns = [
            r'(?:best|top)\s+(?:dealer|shop|business)\s+(?:of|in)\s+\d{4}',
            r'(?:#1|number one|first)\s+(?:in|for)\s+[^.]{10,50}',
            r'(?:certified|authorized)\s+(?:dealer|retailer)\s+(?:for|of)\s+\w+'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches[:2]:
                if match not in intelligence.recent_wins:
                    intelligence.recent_wins.append(match)
    
    def _identify_pain_points(
        self,
        text: str,
        url: str,
        intelligence: PersonalizationIntelligence
    ):
        """Identify potential pain points and opportunities."""
        
        # Website issues
        if intelligence.website_url and intelligence.website_url.startswith('http://'):
            intelligence.website_issues.append("No SSL certificate")
            intelligence.pain_points_addressed.append("Secure website with SSL")
        
        # Check for outdated copyright
        copyright_match = re.search(r'©\s*(\d{4})', text)
        if copyright_match:
            year = int(copyright_match.group(1))
            if year < datetime.now().year - 1:
                intelligence.website_issues.append(f"Outdated copyright ({year})")
                intelligence.pain_points_addressed.append("Website content updates needed")
        
        # Check for missing capabilities in text
        text_lower = text.lower()
        
        # Online capabilities check
        if 'schedule online' not in text_lower and 'book online' not in text_lower:
            intelligence.missing_capabilities.append("No online scheduling")
            intelligence.pain_points_addressed.append("Add online appointment booking")
        
        if 'inventory' not in text_lower and 'browse' not in text_lower:
            intelligence.missing_capabilities.append("No online inventory")
            intelligence.pain_points_addressed.append("Display inventory online")
        
        # Mobile optimization check
        if 'mobile' not in text_lower and 'responsive' not in text_lower:
            intelligence.website_issues.append("May not be mobile-optimized")
            intelligence.pain_points_addressed.append("Mobile-friendly website")
        
        # Social media presence
        if not intelligence.social_media_profiles:
            intelligence.missing_capabilities.append("Limited social media presence")
            intelligence.pain_points_addressed.append("Social media marketing")
        
        # Reviews presence
        if 'review' not in text_lower and 'testimonial' not in text_lower:
            intelligence.missing_capabilities.append("No customer reviews displayed")
            intelligence.pain_points_addressed.append("Review management system")
    
    def _cross_reference_data(self, intelligence: PersonalizationIntelligence):
        """Cross-reference data from multiple sources for validation."""
        
        # Deduplicate lists
        intelligence.primary_services = list(set(intelligence.primary_services))[:10]
        intelligence.recent_wins = list(set(intelligence.recent_wins))[:5]
        intelligence.company_values = list(set(intelligence.company_values))[:5]
        intelligence.website_issues = list(set(intelligence.website_issues))[:5]
        intelligence.missing_capabilities = list(set(intelligence.missing_capabilities))[:5]
        
        # Deduplicate decision makers by name
        seen_names = set()
        unique_decision_makers = []
        for dm in intelligence.key_decision_makers:
            if dm['name'] not in seen_names:
                seen_names.add(dm['name'])
                unique_decision_makers.append(dm)
        intelligence.key_decision_makers = unique_decision_makers[:10]
        
        # Sort announcements by date (if possible)
        intelligence.recent_announcements = intelligence.recent_announcements[:5]
        
        # Limit testimonials
        intelligence.customer_success_stories = intelligence.customer_success_stories[:5]
    
    def _generate_personalization_elements(self, intelligence: PersonalizationIntelligence):
        """Generate personalization elements for outreach."""
        
        # Subject lines
        if intelligence.recent_wins:
            intelligence.suggested_subject_lines.append(
                f"Congrats on {intelligence.recent_wins[0][:40]}!"
            )
        
        if intelligence.owner_name:
            first_name = intelligence.owner_name.split()[0]
            intelligence.suggested_subject_lines.append(
                f"{first_name}, quick question about {intelligence.business_name}"
            )
        
        if intelligence.website_issues:
            intelligence.suggested_subject_lines.append(
                f"Quick improvement for {intelligence.business_name}'s website"
            )
        
        # Ice breakers
        if intelligence.community_involvement:
            intelligence.ice_breakers.append(
                f"I admire your involvement with {intelligence.community_involvement[0]}"
            )
        
        if intelligence.customer_success_stories:
            intelligence.ice_breakers.append(
                "Your customer testimonials really stood out to me"
            )
        
        # Value propositions
        if intelligence.missing_capabilities:
            intelligence.value_propositions.append(
                f"I can help you implement {intelligence.missing_capabilities[0].lower()}"
            )
        
        if intelligence.website_issues:
            intelligence.value_propositions.append(
                "Let me modernize your digital presence for better results"
            )
        
        # CTAs
        intelligence.call_to_actions = [
            "Can we schedule a quick 15-minute call this week?",
            "Would you like to see how we've helped similar businesses?",
            "Are you available for a brief coffee chat?"
        ]
    
    def _calculate_confidence(
        self,
        intelligence: PersonalizationIntelligence,
        sources_count: int
    ) -> float:
        """Calculate confidence score."""
        
        score = 0.0
        
        # Source diversity
        score += min(sources_count / 10, 0.2)  # Up to 20% for sources
        
        # Owner information
        if intelligence.owner_name:
            score += 0.2
            if intelligence.owner_email or intelligence.owner_phone:
                score += 0.1
        
        # Business details
        if intelligence.primary_services:
            score += 0.1
        if intelligence.years_in_business:
            score += 0.05
        
        # Personalization value
        if intelligence.recent_announcements or intelligence.recent_wins:
            score += 0.15
        if intelligence.customer_success_stories:
            score += 0.1
        if intelligence.website_issues or intelligence.missing_capabilities:
            score += 0.1
        
        return min(score, 1.0)
    
    def _assess_freshness(self, all_data: List[Dict]) -> str:
        """Assess data freshness."""
        
        current_year = str(datetime.now().year)
        current_month = datetime.now().strftime('%B')
        
        # Check all text for recent dates
        for data in all_data:
            text = data.get('raw_text', '')
            
            if current_month in text and current_year in text:
                return "Very Fresh (current month)"
            elif current_year in text:
                return "Fresh (current year)"
        
        # Check if we found any dates
        for data in all_data:
            if str(datetime.now().year - 1) in data.get('raw_text', ''):
                return "Recent (last year)"
        
        return "Unknown freshness"


# Test function
async def test_multi_scraper():
    """Test the multi-URL scraper."""
    
    scraper = MultiURLScraperV2(max_urls=5, parallel_limit=2)
    
    # Simulate search results
    search_results = [
        {
            'link': 'https://sunbiz.org/company/12345',
            'title': 'Test Company LLC - Florida Business Registry',
            'snippet': 'Official registration for Test Company LLC'
        },
        {
            'link': 'https://testcompany.com',
            'title': 'Test Company - Official Website',
            'snippet': 'Welcome to Test Company, serving Florida since 1990'
        },
        {
            'link': 'https://yelp.com/biz/test-company',
            'title': 'Test Company - Yelp',
            'snippet': '4.5 stars, 120 reviews'
        }
    ]
    
    intelligence = await scraper.scrape_multiple_sources(
        company_name="Test Company",
        search_results=search_results,
        location="Florida"
    )
    
    print("\n" + "="*60)
    print("MULTI-SOURCE EXTRACTION RESULTS")
    print("="*60)
    
    print(f"\n🏢 Company: {intelligence.business_name}")
    print(f"👤 Owner: {intelligence.owner_name} ({intelligence.owner_title})")
    print(f"📊 Sources Analyzed: {len(intelligence.sources_analyzed)}")
    print(f"🎯 Confidence: {intelligence.extraction_confidence:.1%}")
    print(f"📅 Data Freshness: {intelligence.data_freshness}")
    
    print(f"\n🏆 Achievements:")
    for win in intelligence.recent_wins[:2]:
        print(f"  - {win}")
    
    print(f"\n⚠️ Pain Points:")
    for issue in intelligence.website_issues[:2]:
        print(f"  - {issue}")
    
    print(f"\n💡 Personalization Elements:")
    print(f"  Subject Lines: {len(intelligence.suggested_subject_lines)}")
    print(f"  Ice Breakers: {len(intelligence.ice_breakers)}")
    print(f"  Value Props: {len(intelligence.value_propositions)}")
    
    return intelligence


if __name__ == "__main__":
    asyncio.run(test_multi_scraper())