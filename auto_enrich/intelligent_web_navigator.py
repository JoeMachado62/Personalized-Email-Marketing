"""
Intelligent multi-page web navigator for dealership websites.
Automatically discovers and scrapes relevant pages while avoiding inventory.
"""

import asyncio
import logging
import re
from typing import Dict, List, Any, Optional, Set
from urllib.parse import urljoin, urlparse
from markdownify import markdownify as md
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class IntelligentWebNavigator:
    """
    Smart website navigator that finds and extracts content from relevant pages.
    Focuses on About, Team, Contact, News, and Community pages while avoiding inventory.
    """
    
    # Pages we want to visit (high value for personalization)
    TARGET_PATTERNS = {
        'about': [
            r'/about(?:us)?/?',
            r'/our-story/?',
            r'/who-we-are/?',
            r'/company/?',
            r'/history/?'
        ],
        'team': [
            r'/meet(?:our)?staff/?',
            r'/(?:meet-the-)?(?:team|staff)/?',
            r'/our-(?:team|people|staff)/?',
            r'/employees?/?',
            r'/people/?',
            r'/leadership/?'
        ],
        'contact': [
            r'/contact(?:us)?/?',
            r'/sendcomments/?',
            r'/location/?',
            r'/directions/?',
            r'/hours/?',
            r'/get-in-touch/?'
        ],
        'news': [
            r'/news/?',
            r'/blog/?',
            r'/updates?/?',
            r'/press(?:-releases)?/?',
            r'/media/?',
            r'/articles?/?'
        ],
        'community': [
            r'/community/?',
            r'/charity/?',
            r'/giving-back/?',
            r'/social-responsibility/?',
            r'/events/?',
            r'/sponsorships?/?'
        ],
        'testimonials': [
            r'/testimonials?/?',
            r'/reviews?/?',
            r'/customer-(?:reviews|testimonials)/?',
            r'/success-stories/?',
            r'/feedback/?'
        ],
        'services': [
            r'/services?/?',
            r'/what-we-do/?',
            r'/financing/?',
            r'/trade-in/?',
            r'/warranty/?'
        ]
    }
    
    # Pages to avoid (low value, high noise)
    AVOID_PATTERNS = [
        r'/inventory',
        r'/vehicles?',
        r'/search',
        r'/cars?(?:-|/)',
        r'/trucks?(?:-|/)',
        r'/suvs?(?:-|/)',
        r'/(?:new|used|pre-owned)(?:-|/)',
        r'/browse',
        r'/listings?',
        r'/stock',
        r'/vin/',
        r'/model/',
        r'/make/',
        r'/finance-application',
        r'/credit-app',
        r'/privacy',
        r'/terms',
        r'/sitemap',
        r'/login',
        r'/register',
        r'\.pdf$',
        r'\.jpg$',
        r'\.png$'
    ]
    
    def __init__(self, max_pages: int = 15, max_content_per_page: int = 20000):
        """
        Initialize the navigator.
        
        Args:
            max_pages: Maximum number of pages to visit
            max_content_per_page: Maximum characters to extract per page
        """
        self.max_pages = max_pages
        self.max_content_per_page = max_content_per_page
        self.visited_urls: Set[str] = set()
        self.stealth_enabled = True
        
    async def navigate_and_extract(self, base_url: str) -> Dict[str, Any]:
        """
        Navigate website and extract comprehensive content.
        
        Args:
            base_url: The website's homepage URL
            
        Returns:
            Dictionary with extracted content from all relevant pages
        """
        logger.info(f"Starting intelligent navigation of {base_url}")
        
        # Parse base URL
        parsed_base = urlparse(base_url)
        self.base_domain = f"{parsed_base.scheme}://{parsed_base.netloc}"
        # Normalized host variants for robust same-site checks
        self.base_host = parsed_base.netloc.lower()
        self.base_root = self.base_host[4:] if self.base_host.startswith('www.') else self.base_host
        logger.info(f"Base domain: {self.base_domain} (host={self.base_host}, root={self.base_root})")
        
        # Initialize results
        results = {
            'base_url': base_url,
            'pages_scraped': 0,
            'total_content_chars': 0,
            'content_by_category': {},
            'team_members': [],
            'contact_info': {},
            'key_information': {},
            'all_content': [],  # All content for AI processing
            'errors': []
        }
        
        try:
            # Use Playwright for navigation
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--disable-blink-features=AutomationControlled']
                )
                
                # Enhanced stealth configuration based on modern techniques
                import random
                
                context = await browser.new_context(
                    user_agent=self._get_random_user_agent(),
                    viewport={
                        'width': 1920 + random.randint(-100, 100),  # Randomize viewport
                        'height': 1080 + random.randint(-100, 100)
                    },
                    locale='en-US',
                    timezone_id='America/New_York',
                    permissions=['geolocation', 'notifications'],
                    geolocation={'latitude': 40.7128, 'longitude': -74.0060},
                    color_scheme='light',
                    device_scale_factor=1 + (random.randint(-10, 10) / 100),  # 0.9 to 1.1
                    is_mobile=False,
                    has_touch=False,
                    reduced_motion='no-preference',
                    extra_http_headers={
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                        'Sec-Ch-Ua-Mobile': '?0',
                        'Sec-Ch-Ua-Platform': '"Windows"',
                        'Sec-Fetch-Dest': 'document',
                        'Sec-Fetch-Mode': 'navigate',
                        'Sec-Fetch-Site': 'none',
                        'Sec-Fetch-User': '?1',
                        'Upgrade-Insecure-Requests': '1'
                    }
                )
                
                # Start with homepage
                page = await context.new_page()
                
                # Apply advanced stealth techniques
                if self.stealth_enabled:
                    await self._apply_stealth_scripts(page)
                
                # Extract homepage and discover links
                homepage_content, discovered_links = await self._extract_page_with_links(
                    page, base_url, 'homepage'
                )
                
                if homepage_content:
                    results['content_by_category']['homepage'] = homepage_content
                    results['all_content'].append(homepage_content)
                    results['pages_scraped'] += 1
                    results['total_content_chars'] += len(homepage_content.get('markdown', ''))
                    self.visited_urls.add(base_url)
                
                # Find target pages from discovered links
                target_urls = self._find_target_pages(discovered_links)
                
                # Visit each target page
                try:
                    logger.info(f"Target URLs to visit: {{ {', '.join([f'{k}: {len(v)}' for k, v in target_urls.items()])} }}")
                except Exception:
                    pass
                for category, urls in target_urls.items():
                    if results['pages_scraped'] >= self.max_pages:
                        break
                        
                    for url in urls[:2]:  # Max 2 pages per category
                        if url in self.visited_urls:
                            continue
                            
                        if results['pages_scraped'] >= self.max_pages:
                            break
                        
                        logger.info(f"Visiting {category} page: {url}")
                        
                        try:
                            content, _ = await self._extract_page_with_links(
                                page, url, category
                            )
                            
                            if content:
                                # Store content by category
                                if category not in results['content_by_category']:
                                    results['content_by_category'][category] = []
                                results['content_by_category'][category].append(content)
                                results['all_content'].append(content)
                                
                                # Extract specific information
                                if category == 'team':
                                    team = self._extract_team_members(content)
                                    results['team_members'].extend(team)
                                
                                if category == 'contact':
                                    contact = self._extract_contact_info(content)
                                    results['contact_info'].update(contact)
                                
                                results['pages_scraped'] += 1
                                results['total_content_chars'] += len(content.get('markdown', ''))
                                self.visited_urls.add(url)
                                
                        except Exception as e:
                            logger.error(f"Error extracting {url}: {e}")
                            results['errors'].append(f"{url}: {str(e)}")
                
                # Visit news/blog pages if we have room
                if results['pages_scraped'] < self.max_pages and 'news' in target_urls:
                    for url in target_urls['news'][:3]:  # Get up to 3 recent news items
                        if url in self.visited_urls:
                            continue
                        if results['pages_scraped'] >= self.max_pages:
                            break
                            
                        try:
                            content, _ = await self._extract_page_with_links(
                                page, url, 'news'
                            )
                            
                            if content:
                                if 'news' not in results['content_by_category']:
                                    results['content_by_category']['news'] = []
                                results['content_by_category']['news'].append(content)
                                results['all_content'].append(content)
                                results['pages_scraped'] += 1
                                results['total_content_chars'] += len(content.get('markdown', ''))
                                self.visited_urls.add(url)
                                
                        except Exception as e:
                            logger.error(f"Error extracting news {url}: {e}")
                
                await browser.close()
                
        except Exception as e:
            logger.error(f"Navigation error: {e}")
            results['errors'].append(f"Navigation failed: {str(e)}")
        
        # Process and prioritize content for AI
        results['prioritized_content'] = self._prioritize_content(results)
        
        logger.info(f"Navigation complete: {results['pages_scraped']} pages, "
                   f"{results['total_content_chars']} total chars")
        
        return results
    
    async def _extract_page_with_links(self, page, url: str, category: str) -> tuple:
        """
        Extract content from a page and discover links.
        
        Returns:
            Tuple of (content_dict, discovered_links)
        """
        try:
            # Navigate to page with better wait strategy
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            
            # Intelligent wait strategy for dynamic content
            await self._intelligent_wait_for_content(page)
            
            # Wait for content to load
            try:
                await page.wait_for_load_state('networkidle', timeout=10000)
            except:
                pass  # Some pages never reach networkidle
            
            # Simulate human behavior to avoid detection
            if self.stealth_enabled:
                await self._simulate_human_behavior(page)
            
            # Get page title
            title = await page.title()
            
            # Wait a bit more for dynamic content
            await asyncio.sleep(2)
            
            # Get all links on the page (including dynamically loaded)
            links = await page.evaluate("""
                () => {
                    const links = [];
                    // Wait for any lazy-loaded content
                    const allLinks = document.querySelectorAll('a[href]');
                    allLinks.forEach(a => {
                        if (a.href && a.href.length > 0) {
                            links.push({
                                href: a.href,
                                text: (a.innerText || a.textContent || '').trim(),
                                title: a.title || ''
                            });
                        }
                    });
                    return links;
                }
            """)
            logger.info(f"Discovered {len(links)} links on {url}")
            
            # Get full HTML
            html_content = await page.content()
            
            # Clean and convert to markdown
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script, style, and other non-content elements
            for element in soup(["script", "style", "meta", "link", "noscript", "header", "footer", "nav"]):
                element.decompose()
            
            # Get cleaned HTML
            cleaned_html = str(soup)
            
            # Convert to markdown
            markdown_content = md(cleaned_html, 
                                heading_style="ATX",
                                bullets='-',
                                code_language='',
                                escape_misc=False)
            
            # Clean up excessive whitespace
            markdown_content = re.sub(r'\n{3,}', '\n\n', markdown_content)
            
            # Check if content is too small (likely JavaScript-rendered)
            if len(markdown_content.strip()) < 500:
                logger.warning(f"Low content detected ({len(markdown_content)} chars), using fallback extraction")
                fallback_content = await self._extract_with_fallback(page, url)
                if len(fallback_content) > len(markdown_content):
                    markdown_content = fallback_content
                    logger.info(f"Fallback extraction improved content: {len(fallback_content)} chars")
            
            # Truncate if needed
            if len(markdown_content) > self.max_content_per_page:
                markdown_content = markdown_content[:self.max_content_per_page]
            
            content = {
                'url': url,
                'title': title,
                'category': category,
                'markdown': markdown_content,
                'char_count': len(markdown_content),
                'raw_html': html_content if category == 'team' else None  # Keep HTML for team parsing
            }
            
            return content, links
            
        except Exception as e:
            logger.error(f"Error extracting {url}: {e}")
            return None, []
    
    def _find_target_pages(self, links: List[Dict]) -> Dict[str, List[str]]:
        """
        Find target pages from discovered links.
        
        Returns:
            Dictionary mapping categories to URLs
        """
        target_urls = {}
        
        logger.info(f"Processing {len(links)} links (base_root={getattr(self, 'base_root', '')})")

        for link in links:
            if not link.get('href'):
                continue
                
            href = link['href']
            text = link.get('text', '').lower()
            
            # Parse the URL path
            from urllib.parse import urlparse
            parsed = urlparse(href)
            path = parsed.path.lower()
            
            # Skip if it's an external link (different domain), allowing http/https and www variants
            host = parsed.netloc.lower()
            def _norm(h: str) -> str:
                return h[4:] if h.startswith('www.') else h
            if host and hasattr(self, 'base_root') and not _norm(host).endswith(self.base_root):
                continue
            
            # Skip if it matches avoid patterns
            if any(re.search(pattern, path) for pattern in self.AVOID_PATTERNS):
                continue
            
            # Check against target patterns
            for category, patterns in self.TARGET_PATTERNS.items():
                for pattern in patterns:
                    if re.search(pattern, path) or (
                        category in text and len(text) < 50
                    ):
                        if category not in target_urls:
                            target_urls[category] = []
                        if href not in target_urls[category]:
                            target_urls[category].append(href)
                        break
        
        try:
            logger.info(f"Found target pages: {{ {', '.join([f'{k}: {len(v)}' for k, v in target_urls.items()])} }}")
        except Exception:
            logger.info(f"Found target pages: {list(target_urls.keys())}")
        
        return target_urls
    
    def _extract_team_members(self, content: Dict) -> List[Dict]:
        """
        Extract team member information from content.
        """
        team = []
        
        if not content.get('markdown'):
            return team
        
        # Look for common team member patterns
        lines = content['markdown'].split('\n')
        current_member = {}
        
        for line in lines:
            line = line.strip()
            
            # Look for name patterns (usually in headers or bold)
            if line.startswith('#') or line.startswith('**'):
                # Check if it looks like a person's name
                clean_line = re.sub(r'[#*]', '', line).strip()
                if len(clean_line.split()) in [2, 3] and not any(
                    word in clean_line.lower() 
                    for word in ['team', 'staff', 'our', 'meet', 'the', 'page']
                ):
                    # Save previous member if exists
                    if current_member:
                        team.append(current_member)
                    
                    current_member = {'name': clean_line, 'info': []}
            
            # Collect info about current member
            elif current_member and line:
                # Look for title/position
                if any(word in line.lower() for word in 
                      ['manager', 'director', 'president', 'owner', 'sales', 
                       'finance', 'service', 'parts', 'advisor']):
                    current_member['title'] = line
                    current_member['info'].append(line)
                # Look for contact info
                elif '@' in line or re.search(r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}', line):
                    current_member['info'].append(line)
                # Collect bio info (limit to 200 chars)
                elif len(' '.join(current_member['info'])) < 200:
                    current_member['info'].append(line)
        
        # Add last member
        if current_member:
            team.append(current_member)
        
        return team
    
    def _extract_contact_info(self, content: Dict) -> Dict:
        """
        Extract contact information from content.
        """
        contact = {}
        
        if not content.get('markdown'):
            return contact
        
        text = content['markdown']
        
        # Extract phone numbers
        phones = re.findall(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text)
        if phones:
            contact['phones'] = list(set(phones))
        
        # Extract email addresses
        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
        if emails:
            contact['emails'] = list(set(emails))
        
        # Extract addresses
        address_pattern = r'\d+\s+[\w\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Court|Ct)'
        addresses = re.findall(address_pattern, text, re.IGNORECASE)
        if addresses:
            contact['addresses'] = addresses[:2]  # Keep top 2
        
        # Extract hours
        hours_pattern = r'(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)[:\s]+[\d:apmAPM\s-]+'
        hours = re.findall(hours_pattern, text)
        if hours:
            contact['hours'] = hours
        
        return contact
    
    def _prioritize_content(self, results: Dict) -> str:
        """
        Prioritize and combine content for AI processing.
        Target: ~80,000 chars (20,000 tokens)
        """
        prioritized = []
        char_limit = 80000
        current_chars = 0
        
        # Priority 1: Team members (highest value)
        if results['team_members']:
            team_text = "\n## TEAM MEMBERS\n"
            for member in results['team_members'][:20]:  # Limit to 20 team members
                team_text += f"- {member.get('name', 'Unknown')}"
                if member.get('title'):
                    team_text += f" - {member['title']}"
                if member.get('info'):
                    team_text += f" - {' '.join(member['info'][:2])}"
                team_text += "\n"
            
            prioritized.append(team_text)
            current_chars += len(team_text)
        
        # Priority 2: About Us content
        if 'about' in results['content_by_category']:
            about_content = "\n## ABOUT THE COMPANY\n"
            for content in results['content_by_category']['about']:
                if current_chars + len(content['markdown']) > char_limit:
                    remaining = char_limit - current_chars
                    about_content += content['markdown'][:remaining]
                    break
                about_content += content['markdown']
                about_content += "\n---\n"
            
            prioritized.append(about_content)
            current_chars += len(about_content)
        
        # Priority 3: Recent news/community involvement
        if 'news' in results['content_by_category'] and current_chars < char_limit:
            news_content = "\n## RECENT NEWS & COMMUNITY INVOLVEMENT\n"
            for content in results['content_by_category']['news'][:3]:
                if current_chars + len(content['markdown']) > char_limit:
                    remaining = char_limit - current_chars
                    news_content += content['markdown'][:remaining]
                    break
                news_content += f"### {content.get('title', 'News Item')}\n"
                news_content += content['markdown'][:2000]  # Limit each news item
                news_content += "\n---\n"
                current_chars += 2000
            
            prioritized.append(news_content)
        
        # Priority 4: Community/charity work
        if 'community' in results['content_by_category'] and current_chars < char_limit:
            community_content = "\n## COMMUNITY INVOLVEMENT\n"
            for content in results['content_by_category']['community']:
                if current_chars + len(content['markdown']) > char_limit:
                    remaining = char_limit - current_chars
                    community_content += content['markdown'][:remaining]
                    break
                community_content += content['markdown']
                current_chars += len(content['markdown'])
            
            prioritized.append(community_content)
        
        # Priority 5: Testimonials
        if 'testimonials' in results['content_by_category'] and current_chars < char_limit:
            testimonial_content = "\n## CUSTOMER TESTIMONIALS\n"
            for content in results['content_by_category']['testimonials']:
                if current_chars + 3000 > char_limit:
                    break
                testimonial_content += content['markdown'][:3000]
                current_chars += 3000
            
            prioritized.append(testimonial_content)
        
        # Priority 6: Services offered
        if 'services' in results['content_by_category'] and current_chars < char_limit:
            services_content = "\n## SERVICES OFFERED\n"
            for content in results['content_by_category']['services']:
                if current_chars + 2000 > char_limit:
                    break
                services_content += content['markdown'][:2000]
                current_chars += 2000
            
            prioritized.append(services_content)
        
        # Priority 7: Homepage content (if room)
        if 'homepage' in results['content_by_category'] and current_chars < char_limit:
            homepage = results['content_by_category']['homepage']
            remaining = char_limit - current_chars
            if remaining > 1000:
                prioritized.append(f"\n## HOMEPAGE EXCERPT\n{homepage['markdown'][:remaining]}")
        
        return '\n'.join(prioritized)
    
    def _get_random_user_agent(self) -> str:
        """Get a random realistic user agent."""
        import random
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        return random.choice(user_agents)
    
    async def _apply_stealth_scripts(self, page) -> None:
        """Apply advanced stealth scripts to avoid detection."""
        # Override navigator properties
        await page.add_init_script("""
            // Override navigator.webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Override navigator.plugins to look realistic
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    {0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format", enabledPlugin: Plugin}, description: "Portable Document Format", filename: "internal-pdf-viewer", length: 1, name: "Chrome PDF Plugin"},
                    {0: {type: "application/pdf", suffixes: "pdf", description: "", enabledPlugin: Plugin}, description: "", filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai", length: 1, name: "Chrome PDF Viewer"},
                    {0: {type: "application/x-nacl", suffixes: "", description: "Native Client Executable", enabledPlugin: Plugin}, 1: {type: "application/x-pnacl", suffixes: "", description: "Portable Native Client Executable", enabledPlugin: Plugin}, description: "", filename: "internal-nacl-plugin", length: 2, name: "Native Client"}
                ]
            });
            
            // Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            
            // Add realistic window.chrome object
            if (!window.chrome) {
                window.chrome = {
                    runtime: {},
                    loadTimes: function() {
                        return {
                            requestTime: Date.now() / 1000,
                            startLoadTime: Date.now() / 1000,
                            commitLoadTime: Date.now() / 1000 - 0.5,
                            finishDocumentLoadTime: Date.now() / 1000 - 0.3,
                            finishLoadTime: Date.now() / 1000 - 0.1,
                            firstPaintTime: Date.now() / 1000 - 0.4,
                            firstPaintAfterLoadTime: 0,
                            navigationType: "Other",
                            wasFetchedViaSpdy: false,
                            wasNpnNegotiated: true,
                            npnNegotiatedProtocol: "h2",
                            wasAlternateProtocolAvailable: false,
                            connectionInfo: "h2"
                        };
                    },
                    csi: function() {
                        return {
                            onloadT: Date.now(),
                            pageT: Date.now() - Math.random() * 1000,
                            startE: Date.now() - Math.random() * 2000,
                            tran: 15
                        };
                    }
                };
            }
            
            // Override WebGL vendor and renderer
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) {
                    return 'Intel Inc.';
                }
                if (parameter === 37446) {
                    return 'Intel Iris OpenGL Engine';
                }
                return getParameter.call(this, parameter);
            };
            
            // Override hardware concurrency with realistic value
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 4 + Math.floor(Math.random() * 4) * 2  // 4, 6, 8, 10, or 12
            });
            
            // Override screen properties
            Object.defineProperty(screen, 'colorDepth', { get: () => 24 });
            Object.defineProperty(screen, 'pixelDepth', { get: () => 24 });
            
            // Add realistic battery API
            if ('getBattery' in navigator) {
                const originalGetBattery = navigator.getBattery;
                navigator.getBattery = async () => {
                    const battery = await originalGetBattery.call(navigator);
                    Object.defineProperty(battery, 'charging', { get: () => true });
                    Object.defineProperty(battery, 'chargingTime', { get: () => 0 });
                    Object.defineProperty(battery, 'dischargingTime', { get: () => Infinity });
                    Object.defineProperty(battery, 'level', { get: () => 0.7 + Math.random() * 0.3 });
                    return battery;
                };
            }
            
            // Override languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
            
            // Add touch support detection countermeasure
            Object.defineProperty(navigator, 'maxTouchPoints', {
                get: () => 0
            });
            
            // Override automation indicators
            delete window.navigator.__proto__.webdriver;
            
            // Make notification API look realistic
            if ('Notification' in window) {
                const OriginalNotification = window.Notification;
                window.Notification = new Proxy(Notification, {
                    construct(target, args) {
                        return new OriginalNotification(...args);
                    }
                });
                window.Notification.permission = 'default';
                window.Notification.requestPermission = () => Promise.resolve('default');
            }
        """)
    
    async def _simulate_human_behavior(self, page) -> None:
        """Simulate human-like behavior on the page."""
        import random
        import asyncio
        
        try:
            # Random delay between 0.5 and 2 seconds
            await asyncio.sleep(random.uniform(0.5, 2))
            
            # Simulate mouse movement
            viewport_size = await page.viewport_size()
            if viewport_size:
                width = viewport_size['width']
                height = viewport_size['height']
                
                # Move mouse in a curved path
                steps = random.randint(3, 7)
                for i in range(steps):
                    x = random.randint(100, width - 100)
                    y = random.randint(100, height - 100)
                    await page.mouse.move(x, y, steps=random.randint(10, 30))
                    await asyncio.sleep(random.uniform(0.1, 0.3))
            
            # Random scroll behavior
            scroll_attempts = random.randint(1, 3)
            for _ in range(scroll_attempts):
                # Scroll down
                scroll_distance = random.randint(100, 500)
                await page.evaluate(f"window.scrollBy(0, {scroll_distance})")
                await asyncio.sleep(random.uniform(0.5, 1.5))
                
                # Sometimes scroll back up a bit
                if random.random() > 0.7:
                    await page.evaluate(f"window.scrollBy(0, -{scroll_distance // 2})")
                    await asyncio.sleep(random.uniform(0.3, 0.7))
            
            # Simulate reading time
            await asyncio.sleep(random.uniform(1, 3))
            
            # Random mouse hover over elements
            elements = await page.query_selector_all('a, button, input')
            if elements and len(elements) > 0:
                # Hover over 1-3 random elements
                hover_count = min(len(elements), random.randint(1, 3))
                for _ in range(hover_count):
                    element = random.choice(elements)
                    try:
                        await element.hover()
                        await asyncio.sleep(random.uniform(0.2, 0.5))
                    except:
                        pass
            
            # Move mouse to neutral position
            if viewport_size:
                await page.mouse.move(
                    viewport_size['width'] // 2 + random.randint(-50, 50),
                    viewport_size['height'] // 2 + random.randint(-50, 50),
                    steps=random.randint(5, 15)
                )
        
        except Exception as e:
            logger.debug(f"Human behavior simulation error (non-critical): {e}")
    
    async def _intelligent_wait_for_content(self, page) -> None:
        """
        Intelligently wait for dynamic content to load using multiple strategies.
        """
        import asyncio
        
        try:
            # Strategy 1: Wait for common loading indicators to disappear
            loading_selectors = [
                '.loading', '.loader', '.spinner', '#loading',
                '[class*="loading"]', '[class*="loader"]', '[class*="spinner"]',
                '.skeleton', '.placeholder'
            ]
            
            for selector in loading_selectors:
                try:
                    # Wait for loader to appear and then disappear
                    await page.wait_for_selector(selector, timeout=1000, state='attached')
                    await page.wait_for_selector(selector, timeout=10000, state='hidden')
                    logger.debug(f"Waited for {selector} to disappear")
                except:
                    pass  # Loader not found or already hidden
            
            # Strategy 2: Wait for content indicators
            content_selectors = [
                'main', 'article', '#content', '.content',
                '[role="main"]', '.container', '#main'
            ]
            
            content_found = False
            for selector in content_selectors:
                try:
                    element = await page.wait_for_selector(selector, timeout=2000, state='visible')
                    if element:
                        # Wait for the content to have actual text
                        await page.wait_for_function(
                            f"""() => {{
                                const el = document.querySelector('{selector}');
                                return el && el.innerText && el.innerText.trim().length > 100;
                            }}""",
                            timeout=5000
                        )
                        content_found = True
                        logger.debug(f"Content loaded in {selector}")
                        break
                except:
                    pass
            
            # Strategy 3: Check for JavaScript frameworks
            framework_check = await page.evaluate("""() => {
                // Check for common JS frameworks that might be loading content
                const frameworks = {
                    react: window.React || document.querySelector('[data-reactroot]'),
                    angular: window.angular || document.querySelector('[ng-app]'),
                    vue: window.Vue || document.querySelector('#app'),
                    nextjs: window.__NEXT_DATA__,
                    gatsby: window.___gatsby
                };
                
                for (const [name, indicator] of Object.entries(frameworks)) {
                    if (indicator) return name;
                }
                return null;
            }""")
            
            if framework_check:
                logger.debug(f"Detected {framework_check} framework - waiting longer")
                await asyncio.sleep(3)  # Extra wait for SPA frameworks
            
            # Strategy 4: Monitor DOM mutations
            await page.evaluate("""() => {
                return new Promise((resolve) => {
                    let changeCount = 0;
                    let lastChangeTime = Date.now();
                    
                    const observer = new MutationObserver(() => {
                        changeCount++;
                        lastChangeTime = Date.now();
                    });
                    
                    observer.observe(document.body, {
                        childList: true,
                        subtree: true,
                        characterData: true
                    });
                    
                    // Wait until DOM is stable (no changes for 1 second)
                    const checkInterval = setInterval(() => {
                        const timeSinceLastChange = Date.now() - lastChangeTime;
                        if (timeSinceLastChange > 1000 || Date.now() - startTime > 5000) {
                            observer.disconnect();
                            clearInterval(checkInterval);
                            resolve(changeCount);
                        }
                    }, 200);
                    
                    const startTime = Date.now();
                });
            }""")
            
            # Strategy 5: Check for lazy-loaded images
            await page.evaluate("""() => {
                const images = document.querySelectorAll('img[data-src], img.lazy, img[loading="lazy"]');
                const promises = Array.from(images).map(img => {
                    if (img.complete) return Promise.resolve();
                    return new Promise(resolve => {
                        img.addEventListener('load', resolve);
                        img.addEventListener('error', resolve);
                        setTimeout(resolve, 2000); // Timeout after 2s per image
                    });
                });
                return Promise.all(promises);
            }""")
            
            # Final safety wait
            await asyncio.sleep(1)
            
        except Exception as e:
            logger.debug(f"Intelligent wait error (non-critical): {e}")
            # Fallback to simple wait
            await asyncio.sleep(3)
    
    async def _extract_with_fallback(self, page, url: str) -> str:
        """
        Extract content with multiple fallback strategies for JavaScript-heavy sites.
        """
        content = ""
        
        try:
            # Method 1: Standard extraction
            content = await page.evaluate("""() => {
                // Try to get main content area
                const contentSelectors = [
                    'main', 'article', '#content', '.content',
                    '[role="main"]', '.container', '#main', 'body'
                ];
                
                for (const selector of contentSelectors) {
                    const element = document.querySelector(selector);
                    if (element && element.innerText && element.innerText.trim().length > 100) {
                        return element.innerText;
                    }
                }
                
                // Fallback to body
                return document.body.innerText || '';
            }""")
            
            if len(content) < 100:
                # Method 2: Wait and retry with different strategy
                await asyncio.sleep(2)
                
                # Scroll to trigger lazy loading
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(1)
                await page.evaluate("window.scrollTo(0, 0)")
                await asyncio.sleep(1)
                
                # Try shadow DOM extraction
                content = await page.evaluate("""() => {
                    function extractFromShadowDOM(root) {
                        let text = '';
                        
                        // Get regular content
                        if (root.innerText) {
                            text += root.innerText + '\\n';
                        }
                        
                        // Check for shadow roots
                        const allElements = root.querySelectorAll('*');
                        for (const element of allElements) {
                            if (element.shadowRoot) {
                                text += extractFromShadowDOM(element.shadowRoot) + '\\n';
                            }
                        }
                        
                        return text;
                    }
                    
                    return extractFromShadowDOM(document.body);
                }""")
            
            if len(content) < 100:
                # Method 3: Get all text nodes directly
                content = await page.evaluate("""() => {
                    const walker = document.createTreeWalker(
                        document.body,
                        NodeFilter.SHOW_TEXT,
                        {
                            acceptNode: function(node) {
                                // Skip script and style text
                                const parent = node.parentElement;
                                if (parent && (parent.tagName === 'SCRIPT' || parent.tagName === 'STYLE')) {
                                    return NodeFilter.FILTER_REJECT;
                                }
                                // Only accept visible text
                                if (node.nodeValue && node.nodeValue.trim().length > 0) {
                                    return NodeFilter.FILTER_ACCEPT;
                                }
                                return NodeFilter.FILTER_REJECT;
                            }
                        }
                    );
                    
                    let text = '';
                    let node;
                    while (node = walker.nextNode()) {
                        text += node.nodeValue + ' ';
                    }
                    
                    return text;
                }""")
            
            if len(content) < 100:
                # Method 4: Screenshot OCR fallback (indicate need for OCR)
                logger.warning(f"Page {url} appears to be image-heavy or uses canvas rendering")
                content = f"[LOW_CONTENT_WARNING] Page may require OCR or specialized extraction. URL: {url}"
            
        except Exception as e:
            logger.error(f"Fallback extraction error for {url}: {e}")
            content = f"[EXTRACTION_ERROR] Failed to extract content from {url}: {str(e)}"
        
        return content


# Test function
async def test_navigator():
    """Test the intelligent navigator."""
    navigator = IntelligentWebNavigator(max_pages=10)
    
    # Test with a dealership website
    results = await navigator.navigate_and_extract("http://www.gatorcitymotors.com")
    
    print(f"\n=== Navigation Results ===")
    print(f"Pages scraped: {results['pages_scraped']}")
    print(f"Total content: {results['total_content_chars']} chars")
    print(f"Team members found: {len(results['team_members'])}")
    
    print(f"\nCategories found:")
    for category, content in results['content_by_category'].items():
        if isinstance(content, list):
            print(f"  {category}: {len(content)} pages")
        else:
            print(f"  {category}: 1 page")
    
    if results['team_members']:
        print(f"\nTeam Members:")
        for member in results['team_members'][:5]:
            print(f"  - {member.get('name')}: {member.get('title', 'N/A')}")
    
    print(f"\nPrioritized content length: {len(results.get('prioritized_content', ''))} chars")
    
    return results


if __name__ == "__main__":
    asyncio.run(test_navigator())