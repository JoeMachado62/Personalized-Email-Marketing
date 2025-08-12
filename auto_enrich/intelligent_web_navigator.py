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
                
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    viewport={'width': 1920, 'height': 1080}
                )
                
                # Start with homepage
                page = await context.new_page()
                
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
            # Navigate to page
            await page.goto(url, wait_until='domcontentloaded', timeout=15000)
            
            # Wait for content to load
            try:
                await page.wait_for_load_state('networkidle', timeout=5000)
            except:
                pass  # Some pages never reach networkidle
            
            # Get page title
            title = await page.title()
            
            # Get all links on the page
            links = await page.evaluate("""
                () => {
                    const links = [];
                    document.querySelectorAll('a[href]').forEach(a => {
                        links.push({
                            href: a.href,
                            text: a.innerText.trim(),
                            title: a.title
                        });
                    });
                    return links;
                }
            """)
            
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
        
        for link in links:
            if not link.get('href'):
                continue
                
            href = link['href']
            text = link.get('text', '').lower()
            
            # Parse the URL path
            from urllib.parse import urlparse
            parsed = urlparse(href)
            path = parsed.path.lower()
            
            # Skip if it's an external link (different domain)
            if parsed.netloc and self.base_domain not in href:
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