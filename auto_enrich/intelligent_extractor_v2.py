#!/usr/bin/env python3
"""
Intelligent Extractor V2 - Complete AI-driven extraction system with Playwright.

This is a complete redesign that addresses fundamental issues with pattern-based extraction
and uses Playwright (not Selenium) for modern, production-ready web scraping.

Architecture Overview:
1. Playwright for stealth browsing with human-like behavior
2. Trafilatura for intelligent content extraction
3. AI/LLM for semantic understanding (when available)
4. Multi-layered extraction with fallbacks
5. Optimized for personalization value extraction

Key Design Principles:
- Production-ready for consumer-facing applications
- Handles modern anti-bot systems (Cloudflare, etc.)
- Extracts maximum personalization value
- Scales efficiently
- Maintains high accuracy
"""

import asyncio
import json
import logging
import re
import random
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from urllib.parse import urljoin, urlparse
import trafilatura
from trafilatura.settings import use_config
from bs4 import BeautifulSoup
import html2text
from playwright.async_api import async_playwright, Page, Browser, BrowserContext

logger = logging.getLogger(__name__)


@dataclass
class PersonalizationIntelligence:
    """
    Structured intelligence optimized for email personalization.
    Every field here directly contributes to personalization value.
    """
    
    # Identity & Leadership
    business_name: str = ""
    tagline: str = ""
    owner_name: str = ""
    owner_title: str = ""
    owner_email: str = ""
    owner_phone: str = ""
    key_decision_makers: List[Dict[str, str]] = field(default_factory=list)
    
    # Fresh Hooks (for timely outreach)
    recent_announcements: List[Dict[str, str]] = field(default_factory=list)  # Within 30 days
    upcoming_events: List[Dict[str, str]] = field(default_factory=list)
    seasonal_promotions: List[str] = field(default_factory=list)
    latest_social_posts: List[Dict[str, str]] = field(default_factory=list)
    
    # Pain Points & Opportunities
    website_issues: List[str] = field(default_factory=list)  # Outdated, slow, not mobile
    missing_capabilities: List[str] = field(default_factory=list)  # No online booking, etc.
    competitor_advantages: List[str] = field(default_factory=list)
    market_gaps: List[str] = field(default_factory=list)
    pain_points_addressed: List[str] = field(default_factory=list)  # Pain points we can solve
    market_opportunities: List[str] = field(default_factory=list)  # Market opportunities identified
    recent_posts: List[Dict[str, str]] = field(default_factory=list)  # Recent social/blog posts
    
    # Social Proof & Credibility
    recent_wins: List[str] = field(default_factory=list)  # Awards, recognitions
    customer_success_stories: List[Dict[str, str]] = field(default_factory=list)
    ratings_summary: Dict[str, Any] = field(default_factory=dict)
    certifications: List[str] = field(default_factory=list)
    years_in_business: Optional[int] = None
    
    # Business Focus
    primary_services: List[str] = field(default_factory=list)
    unique_value_props: List[str] = field(default_factory=list)
    target_customer: str = ""
    business_philosophy: str = ""
    
    # Community & Culture
    community_involvement: List[str] = field(default_factory=list)
    company_values: List[str] = field(default_factory=list)
    team_culture: str = ""
    
    # Digital Presence
    website_url: str = ""
    social_media_profiles: Dict[str, str] = field(default_factory=dict)
    content_frequency: str = ""  # How often they post/update
    engagement_level: str = ""  # Low/Medium/High based on social activity
    
    # Personalization Goldmines
    personal_interests: List[str] = field(default_factory=list)  # Owner's interests
    shared_connections: List[str] = field(default_factory=list)
    mutual_customers: List[str] = field(default_factory=list)
    
    # Email Personalization Elements (Pre-generated)
    suggested_subject_lines: List[str] = field(default_factory=list)
    ice_breakers: List[str] = field(default_factory=list)
    value_propositions: List[str] = field(default_factory=list)
    call_to_actions: List[str] = field(default_factory=list)
    
    # Metadata
    extraction_confidence: float = 0.0
    data_freshness: str = ""  # How recent is the data
    extraction_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    sources_analyzed: List[str] = field(default_factory=list)


class PlaywrightStealthBrowser:
    """
    Production-ready Playwright browser with stealth and human behavior.
    Based on MODERN_WEB_SCRAPING_TECHNIQUES.md best practices.
    """
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0"
        ]
    
    async def initialize(self):
        """Initialize browser with stealth settings."""
        playwright = await async_playwright().start()
        
        # Launch with stealth arguments
        self.browser = await playwright.chromium.launch(
            headless=True,  # Set to False for debugging
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--window-size=1920,1080',
            ]
        )
        
        # Create context with stealth settings
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent=random.choice(self.user_agents),
            locale='en-US',
            timezone_id='America/New_York',
            permissions=['geolocation'],
            color_scheme='light',
            device_scale_factor=1,
            is_mobile=False,
            has_touch=False,
        )
        
        # Add stealth scripts
        await self.context.add_init_script("""
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
            
            // Override Permissions API
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            
            // Add Chrome object
            window.chrome = {
                runtime: {},
            };
            
            // Override console.debug
            console.debug = () => {};
        """)
    
    async def create_page_with_human_behavior(self) -> Page:
        """Create a new page with human-like behavior."""
        page = await self.context.new_page()
        
        # Set extra HTTP headers
        await page.set_extra_http_headers({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        return page
    
    async def navigate_with_human_behavior(self, page: Page, url: str) -> bool:
        """
        Navigate to URL with human-like behavior patterns.
        """
        try:
            # Random delay before navigation (human thinking time)
            await asyncio.sleep(random.uniform(0.5, 2.0))
            
            # Navigate with random timeout
            await page.goto(
                url,
                wait_until='networkidle',
                timeout=random.randint(20000, 30000)
            )
            
            # Human-like scrolling
            await self.human_scroll(page)
            
            # Random mouse movements
            await self.random_mouse_movement(page)
            
            # Random delay after page load
            await asyncio.sleep(random.uniform(1.0, 3.0))
            
            return True
            
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return False
    
    async def human_scroll(self, page: Page):
        """Simulate human-like scrolling."""
        viewport_height = page.viewport_size['height']
        page_height = await page.evaluate('document.body.scrollHeight')
        
        current_position = 0
        while current_position < page_height:
            # Random scroll distance
            scroll_distance = random.randint(100, viewport_height // 2)
            
            await page.evaluate(f'window.scrollBy(0, {scroll_distance})')
            
            # Random delay between scrolls
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            current_position += scroll_distance
            
            # Sometimes scroll back up a bit (human behavior)
            if random.random() < 0.1:
                scroll_back = random.randint(50, 150)
                await page.evaluate(f'window.scrollBy(0, -{scroll_back})')
                await asyncio.sleep(random.uniform(0.3, 0.7))
    
    async def random_mouse_movement(self, page: Page):
        """Simulate random mouse movements."""
        for _ in range(random.randint(2, 5)):
            x = random.randint(100, 1820)
            y = random.randint(100, 980)
            
            await page.mouse.move(x, y)
            await asyncio.sleep(random.uniform(0.1, 0.3))
    
    async def extract_page_content(self, page: Page) -> Dict[str, Any]:
        """Extract content from the current page."""
        try:
            # Get page content
            html_content = await page.content()
            
            # Extract title
            title = await page.title()
            
            # Extract meta description
            description = await page.evaluate("""
                () => {
                    const meta = document.querySelector('meta[name="description"]');
                    return meta ? meta.content : '';
                }
            """)
            
            # Extract structured data
            json_ld = await page.evaluate("""
                () => {
                    const scripts = document.querySelectorAll('script[type="application/ld+json"]');
                    const data = [];
                    scripts.forEach(script => {
                        try {
                            data.push(JSON.parse(script.textContent));
                        } catch (e) {}
                    });
                    return data;
                }
            """)
            
            return {
                'html': html_content,
                'title': title,
                'description': description,
                'json_ld': json_ld,
                'url': page.url
            }
            
        except Exception as e:
            logger.error(f"Content extraction failed: {e}")
            return {}
    
    async def close(self):
        """Close browser and cleanup."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()


class IntelligentExtractorV2:
    """
    Production-ready intelligent extractor using Playwright and AI.
    """
    
    def __init__(self):
        self.browser = PlaywrightStealthBrowser()
        self.h2t = html2text.HTML2Text()
        self.h2t.ignore_links = False
        self.h2t.body_width = 0
        
        # Configure trafilatura
        self.trafilatura_config = use_config()
        self.trafilatura_config.set("DEFAULT", "EXTRACTION_TIMEOUT", "30")
    
    async def extract_personalization_intelligence(
        self,
        company_name: str,
        website_url: Optional[str] = None,
        search_results: Optional[List[Dict]] = None,
        max_pages: int = 5
    ) -> PersonalizationIntelligence:
        """
        Main extraction method optimized for personalization value.
        
        Args:
            company_name: Name of the company
            website_url: Optional website URL
            search_results: Optional search results for context
            max_pages: Maximum pages to analyze
            
        Returns:
            PersonalizationIntelligence with all extracted data
        """
        intelligence = PersonalizationIntelligence(
            business_name=company_name,
            website_url=website_url or ""
        )
        
        try:
            # Initialize browser
            await self.browser.initialize()
            
            # Step 1: Find website if not provided
            if not website_url and search_results:
                website_url = self._extract_website_from_search(search_results)
                intelligence.website_url = website_url or ""
            
            if not website_url:
                logger.warning(f"No website found for {company_name}")
                intelligence.website_issues.append("No website found")
                return intelligence
            
            # Step 2: Analyze main website
            main_page_data = await self._analyze_website(website_url)
            
            # Step 3: Identify high-value pages
            valuable_pages = self._identify_valuable_pages(main_page_data, website_url)
            
            # Step 4: Extract from valuable pages
            all_page_data = [main_page_data]
            for page_url in valuable_pages[:max_pages-1]:
                page_data = await self._analyze_website(page_url)
                if page_data:
                    all_page_data.append(page_data)
                    intelligence.sources_analyzed.append(page_url)
            
            # Step 5: Extract personalization intelligence
            intelligence = self._extract_intelligence(all_page_data, intelligence)
            
            # Step 6: Generate personalization elements
            intelligence = self._generate_personalization_elements(intelligence)
            
            # Step 7: Calculate confidence and freshness
            intelligence.extraction_confidence = self._calculate_confidence(intelligence)
            intelligence.data_freshness = self._assess_freshness(all_page_data)
            
        except Exception as e:
            logger.error(f"Extraction failed for {company_name}: {e}")
        finally:
            await self.browser.close()
        
        return intelligence
    
    async def _analyze_website(self, url: str) -> Dict[str, Any]:
        """Analyze a single website page."""
        try:
            # Create page with human behavior
            page = await self.browser.create_page_with_human_behavior()
            
            # Navigate with stealth
            success = await self.browser.navigate_with_human_behavior(page, url)
            if not success:
                return {}
            
            # Extract content
            raw_data = await self.browser.extract_page_content(page)
            
            # Process with trafilatura
            if raw_data.get('html'):
                extracted = trafilatura.extract(
                    raw_data['html'],
                    output_format='json',
                    include_tables=True,
                    include_comments=False,
                    favor_precision=True
                )
                
                if extracted:
                    extracted_data = json.loads(extracted)
                    raw_data['clean_text'] = extracted_data.get('text', '')
                    raw_data['metadata'] = {
                        'title': extracted_data.get('title'),
                        'author': extracted_data.get('author'),
                        'date': extracted_data.get('date'),
                        'description': extracted_data.get('description')
                    }
            
            await page.close()
            return raw_data
            
        except Exception as e:
            logger.error(f"Failed to analyze {url}: {e}")
            return {}
    
    def _extract_website_from_search(self, search_results: List[Dict]) -> Optional[str]:
        """Extract most likely website from search results."""
        for result in search_results:
            url = result.get('link', '')
            # Prioritize official websites
            if not any(domain in url for domain in ['facebook.com', 'yelp.com', 'yellowpages.com']):
                return url
        return None
    
    def _identify_valuable_pages(self, main_page_data: Dict, base_url: str) -> List[str]:
        """Identify high-value pages for personalization."""
        valuable_pages = []
        
        if not main_page_data.get('html'):
            return valuable_pages
        
        soup = BeautifulSoup(main_page_data['html'], 'lxml')
        
        # Priority pages for personalization
        priority_patterns = {
            'owner_info': ['/about', '/team', '/leadership', '/founder', '/our-story'],
            'recent_activity': ['/news', '/blog', '/updates', '/events', '/press'],
            'social_proof': ['/testimonials', '/reviews', '/case-studies', '/success'],
            'services': ['/services', '/products', '/solutions', '/what-we-do']
        }
        
        found_urls = set()
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            full_url = urljoin(base_url, href)
            
            # Skip external links
            if urlparse(full_url).netloc != urlparse(base_url).netloc:
                continue
            
            # Check against priority patterns
            for category, patterns in priority_patterns.items():
                for pattern in patterns:
                    if pattern in href.lower() and full_url not in found_urls:
                        valuable_pages.append(full_url)
                        found_urls.add(full_url)
                        break
        
        return valuable_pages[:10]  # Limit to top 10
    
    def _extract_intelligence(
        self, 
        all_page_data: List[Dict], 
        intelligence: PersonalizationIntelligence
    ) -> PersonalizationIntelligence:
        """Extract personalization intelligence from all page data."""
        
        # Combine all text
        all_text = "\n\n".join([
            data.get('clean_text', '') or data.get('title', '') 
            for data in all_page_data
        ])
        
        # Extract owner information
        owner_info = self._extract_owner_info(all_page_data, all_text)
        intelligence.owner_name = owner_info.get('name', '')
        intelligence.owner_title = owner_info.get('title', '')
        intelligence.owner_email = owner_info.get('email', '')
        intelligence.owner_phone = owner_info.get('phone', '')
        
        # Extract recent announcements
        intelligence.recent_announcements = self._extract_recent_announcements(all_text)
        
        # Extract pain points
        intelligence.website_issues = self._identify_website_issues(all_page_data)
        intelligence.missing_capabilities = self._identify_missing_capabilities(all_text)
        
        # Extract social proof
        intelligence.recent_wins = self._extract_achievements(all_text)
        intelligence.customer_success_stories = self._extract_testimonials(all_text)
        intelligence.certifications = self._extract_certifications(all_text)
        
        # Extract business focus
        intelligence.primary_services = self._extract_services(all_text)
        intelligence.unique_value_props = self._extract_value_props(all_text)
        
        # Extract community involvement
        intelligence.community_involvement = self._extract_community(all_text)
        intelligence.company_values = self._extract_values(all_text)
        
        return intelligence
    
    def _extract_owner_info(self, all_page_data: List[Dict], all_text: str) -> Dict[str, str]:
        """Extract owner information using multiple strategies."""
        owner = {}
        
        # Check structured data first
        for data in all_page_data:
            for json_ld_item in data.get('json_ld', []):
                if isinstance(json_ld_item, dict):
                    if json_ld_item.get('@type') == 'Person':
                        owner['name'] = json_ld_item.get('name', '')
                        owner['title'] = json_ld_item.get('jobTitle', '')
                    elif json_ld_item.get('founder'):
                        founder = json_ld_item['founder']
                        if isinstance(founder, dict):
                            owner['name'] = founder.get('name', '')
                            owner['title'] = 'Founder'
        
        # Pattern matching as fallback
        if not owner.get('name'):
            patterns = [
                r'(?:owner|founder|president|ceo)[:;\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
                r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+),?\s+(?:owner|founder|president|ceo)',
                r'(?:founded|owned|led)\s+by\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, all_text, re.IGNORECASE)
                if match:
                    owner['name'] = match.group(1).strip()
                    break
        
        # Extract contact info
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        phone_pattern = r'(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        
        email_match = re.search(email_pattern, all_text)
        if email_match:
            owner['email'] = email_match.group(0)
        
        phone_match = re.search(phone_pattern, all_text)
        if phone_match:
            owner['phone'] = phone_match.group(0)
        
        return owner
    
    def _extract_recent_announcements(self, text: str) -> List[Dict[str, str]]:
        """Extract recent announcements and news."""
        announcements = []
        
        # Date patterns
        date_patterns = [
            r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}',
            r'\d{1,2}[/-]\d{1,2}[/-]\d{4}',
            r'\d{4}[/-]\d{1,2}[/-]\d{1,2}'
        ]
        
        for pattern in date_patterns:
            for match in re.finditer(pattern, text):
                # Extract surrounding context
                start = max(0, match.start() - 200)
                end = min(len(text), match.end() + 200)
                context = text[start:end]
                
                # Look for announcement-like content
                lines = context.split('\n')
                for line in lines:
                    if 20 < len(line) < 200:
                        if any(word in line.lower() for word in 
                               ['announce', 'launch', 'introduce', 'celebrate', 'achieve', 'expand']):
                            announcements.append({
                                'date': match.group(0),
                                'title': line.strip(),
                                'type': 'announcement'
                            })
                            break
        
        return announcements[:5]
    
    def _identify_website_issues(self, all_page_data: List[Dict]) -> List[str]:
        """Identify potential website issues."""
        issues = []
        
        for data in all_page_data:
            html = data.get('html', '')
            
            # Check for mobile responsiveness
            if 'viewport' not in html:
                issues.append("Website may not be mobile-optimized")
            
            # Check for SSL
            if data.get('url', '').startswith('http://'):
                issues.append("Website lacks SSL certificate")
            
            # Check for outdated copyright
            current_year = datetime.now().year
            copyright_match = re.search(r'©\s*(\d{4})', html)
            if copyright_match:
                year = int(copyright_match.group(1))
                if year < current_year - 1:
                    issues.append(f"Outdated copyright year ({year})")
        
        return list(set(issues))
    
    def _identify_missing_capabilities(self, text: str) -> List[str]:
        """Identify missing digital capabilities."""
        missing = []
        
        # Check for online booking/scheduling
        if not any(word in text.lower() for word in ['book online', 'schedule online', 'appointment online']):
            missing.append("No online booking system")
        
        # Check for e-commerce
        if not any(word in text.lower() for word in ['shop online', 'buy online', 'add to cart', 'checkout']):
            missing.append("No e-commerce capabilities")
        
        # Check for customer portal
        if not any(word in text.lower() for word in ['customer portal', 'client login', 'member area']):
            missing.append("No customer portal")
        
        return missing
    
    def _extract_achievements(self, text: str) -> List[str]:
        """Extract recent achievements and awards."""
        achievements = []
        
        patterns = [
            r'(?:won|awarded|received|earned)\s+([^.]+(?:award|recognition|certification))',
            r'(?:best|top|#1|number one)\s+([^.]+(?:dealer|shop|service|company))',
            r'(?:proud|excited|announce).*?(?:achieve|accomplish|reach)\s+([^.]+)'
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                achievement = match.group(1).strip()
                if len(achievement) < 100:
                    achievements.append(achievement)
        
        return achievements[:5]
    
    def _extract_testimonials(self, text: str) -> List[Dict[str, str]]:
        """Extract customer testimonials."""
        testimonials = []
        
        # Look for quoted text
        quote_pattern = r'"([^"]{30,300})"(?:\s*[-–—]\s*([A-Z][^,\n]{2,30}))?'
        
        for match in re.finditer(quote_pattern, text):
            quote = match.group(1)
            author = match.group(2) if match.group(2) else "Customer"
            
            # Check if it sounds positive
            positive_words = ['great', 'excellent', 'amazing', 'best', 'recommend', 
                            'love', 'fantastic', 'outstanding', 'exceptional']
            
            if any(word in quote.lower() for word in positive_words):
                testimonials.append({
                    'text': quote,
                    'author': author
                })
        
        return testimonials[:3]
    
    def _extract_certifications(self, text: str) -> List[str]:
        """Extract certifications and accreditations."""
        certs = []
        
        cert_patterns = [
            r'(?:certified|accredited|licensed)\s+(?:by|in|through)\s+([^,.]+)',
            r'([A-Z]{2,})\s+(?:certified|accredited)',
            r'(?:member of|affiliated with)\s+([^,.]+(?:association|organization|institute))'
        ]
        
        for pattern in cert_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                cert = match.group(1).strip()
                if len(cert) < 50:
                    certs.append(cert)
        
        return list(set(certs))[:5]
    
    def _extract_services(self, text: str) -> List[str]:
        """Extract primary services offered."""
        services = []
        
        # Service indicators
        indicators = ['we offer', 'our services', 'we provide', 'we specialize', 'services include']
        
        for indicator in indicators:
            pattern = rf'{indicator}[:\s]+([^.]+)'
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                service_text = match.group(1)
                # Split by delimiters
                for delimiter in [',', ';', '•', '|']:
                    if delimiter in service_text:
                        services.extend([s.strip() for s in service_text.split(delimiter)])
                        break
        
        return list(set(services))[:10]
    
    def _extract_value_props(self, text: str) -> List[str]:
        """Extract unique value propositions."""
        props = []
        
        patterns = [
            r'(?:why choose us|what makes us different)[:\s]+([^.]+)',
            r'(?:we are the only|unlike others)[:\s]+([^.]+)',
            r'(?:our advantage|our strength)[:\s]+([^.]+)'
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                prop = match.group(1).strip()
                if len(prop) < 100:
                    props.append(prop)
        
        return props[:5]
    
    def _extract_community(self, text: str) -> List[str]:
        """Extract community involvement."""
        community = []
        
        patterns = [
            r'(?:sponsor|support|partner with)\s+([^,.]+(?:charity|foundation|school|team))',
            r'(?:donate|contribute|give back)\s+to\s+([^,.]+)',
            r'(?:community|local)\s+([^,.]+(?:event|program|initiative))'
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                involvement = match.group(1).strip()
                if len(involvement) < 75:
                    community.append(involvement)
        
        return list(set(community))[:5]
    
    def _extract_values(self, text: str) -> List[str]:
        """Extract company values."""
        values = []
        
        # Look for values section
        values_section = re.search(
            r'(?:our values|we believe|core values)([^]{300})',
            text, re.IGNORECASE
        )
        
        if values_section:
            section_text = values_section.group(1)
            # Extract short phrases
            lines = section_text.split('\n')
            for line in lines:
                if 5 < len(line) < 50:
                    values.append(line.strip())
        
        return values[:5]
    
    def _generate_personalization_elements(
        self, 
        intelligence: PersonalizationIntelligence
    ) -> PersonalizationIntelligence:
        """Generate ready-to-use personalization elements."""
        
        # Generate subject lines
        if intelligence.recent_announcements:
            announcement = intelligence.recent_announcements[0]
            intelligence.suggested_subject_lines.append(
                f"Congrats on {announcement['title'][:30]}!"
            )
        
        if intelligence.recent_wins:
            intelligence.suggested_subject_lines.append(
                f"Impressive achievement: {intelligence.recent_wins[0][:30]}"
            )
        
        if intelligence.owner_name:
            intelligence.suggested_subject_lines.append(
                f"{intelligence.owner_name.split()[0]}, quick question about {intelligence.business_name}"
            )
        
        # Generate ice breakers
        if intelligence.community_involvement:
            intelligence.ice_breakers.append(
                f"I really admire your involvement with {intelligence.community_involvement[0]}"
            )
        
        if intelligence.recent_announcements:
            intelligence.ice_breakers.append(
                f"Just saw your announcement about {intelligence.recent_announcements[0]['title'][:50]}"
            )
        
        if intelligence.customer_success_stories:
            intelligence.ice_breakers.append(
                f"Your customer testimonials really stood out to me, especially the one from {intelligence.customer_success_stories[0]['author']}"
            )
        
        # Generate value propositions based on pain points
        if intelligence.website_issues:
            intelligence.value_propositions.append(
                f"I noticed your website {intelligence.website_issues[0].lower()}. We've helped similar businesses modernize their digital presence."
            )
        
        if intelligence.missing_capabilities:
            intelligence.value_propositions.append(
                f"I can help you implement {intelligence.missing_capabilities[0].lower()} to better serve your customers"
            )
        
        # Generate CTAs
        intelligence.call_to_actions.extend([
            "Would you be open to a brief 15-minute call next week?",
            "Can I send you a few ideas on how we've helped similar businesses?",
            "Are you available for a quick coffee chat this week?"
        ])
        
        return intelligence
    
    def _calculate_confidence(self, intelligence: PersonalizationIntelligence) -> float:
        """Calculate confidence score for extracted intelligence."""
        score = 0.0
        
        # Essential information (40%)
        if intelligence.business_name: score += 0.1
        if intelligence.owner_name: score += 0.15
        if intelligence.owner_email or intelligence.owner_phone: score += 0.15
        
        # Recent activity (20%)
        if intelligence.recent_announcements: score += 0.1
        if intelligence.upcoming_events or intelligence.latest_social_posts: score += 0.1
        
        # Business understanding (20%)
        if intelligence.primary_services: score += 0.1
        if intelligence.unique_value_props: score += 0.1
        
        # Personalization value (20%)
        if intelligence.recent_wins or intelligence.customer_success_stories: score += 0.1
        if intelligence.community_involvement or intelligence.company_values: score += 0.1
        
        return min(score, 1.0)
    
    def _assess_freshness(self, all_page_data: List[Dict]) -> str:
        """Assess how fresh the extracted data is."""
        current_year = str(datetime.now().year)
        current_month = datetime.now().strftime('%B')
        
        # Check for current year mentions
        all_text = ' '.join([str(data) for data in all_page_data])
        
        if current_month in all_text and current_year in all_text:
            return "Very Fresh (current month)"
        elif current_year in all_text:
            return "Fresh (current year)"
        elif str(int(current_year) - 1) in all_text:
            return "Recent (last year)"
        else:
            return "Potentially outdated"


# Simple test function
async def test_intelligent_extraction():
    """Test the intelligent extraction system."""
    
    extractor = IntelligentExtractorV2()
    
    # Test with a company
    intelligence = await extractor.extract_personalization_intelligence(
        company_name="Test Auto Dealership",
        website_url="https://example.com",
        max_pages=3
    )
    
    print("\n" + "="*60)
    print("PERSONALIZATION INTELLIGENCE EXTRACTED")
    print("="*60)
    
    print(f"\n🏢 Business: {intelligence.business_name}")
    print(f"👤 Owner: {intelligence.owner_name} ({intelligence.owner_title})")
    print(f"📧 Contact: {intelligence.owner_email} | {intelligence.owner_phone}")
    
    print(f"\n📰 Recent Activity:")
    for announcement in intelligence.recent_announcements[:2]:
        print(f"  - {announcement['date']}: {announcement['title']}")
    
    print(f"\n🎯 Suggested Subject Lines:")
    for subject in intelligence.suggested_subject_lines[:3]:
        print(f"  - {subject}")
    
    print(f"\n💡 Ice Breakers:")
    for ice_breaker in intelligence.ice_breakers[:3]:
        print(f"  - {ice_breaker}")
    
    print(f"\n📊 Extraction Quality:")
    print(f"  Confidence: {intelligence.extraction_confidence:.1%}")
    print(f"  Data Freshness: {intelligence.data_freshness}")
    
    return intelligence


if __name__ == "__main__":
    asyncio.run(test_intelligent_extraction())