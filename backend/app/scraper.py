"""
Web Scraper Module
Handles both static and dynamic (JavaScript-rendered) websites.

Fixed issues:
- Proper timeout enforcement on all requests
- SSL verification with fallback
- Better error handling
- Input validation
- Response size limits
- No infinite redirect loops
"""

import asyncio
import re
from typing import Dict, List, Set, Optional, Tuple
from urllib.parse import urlparse, urljoin, urldefrag
from dataclasses import dataclass, field
import logging

from bs4 import BeautifulSoup
import httpx

try:
    from fake_useragent import UserAgent
    HAS_FAKE_UA = True
except ImportError:
    HAS_FAKE_UA = False

try:
    import tldextract
    HAS_TLDEXTRACT = True
except ImportError:
    HAS_TLDEXTRACT = False

from app.extractors import (
    EmailExtractor,
    PhoneExtractor,
    WhatsAppExtractor,
    SocialLinkExtractor,
    NameExtractor,
    AddressExtractor
)

# Configure logging
logger = logging.getLogger(__name__)

# Constants
MAX_RESPONSE_SIZE = 500000  # 500KB per page
MAX_REDIRECTS = 5
DEFAULT_TIMEOUT = 15
MAX_PAGES_DEFAULT = 10


@dataclass
class ScrapedPage:
    """Represents a scraped page."""
    url: str
    html: str
    text: str
    title: str = ""
    status: int = 200
    error: Optional[str] = None


@dataclass
class ContactData:
    """Aggregated contact information."""
    emails: List[str] = field(default_factory=list)
    phones: List[Dict] = field(default_factory=list)
    whatsapp: List[Dict] = field(default_factory=list)
    social_links: Dict[str, List[Dict]] = field(default_factory=dict)
    names: List[str] = field(default_factory=list)
    addresses: List[str] = field(default_factory=list)
    source_url: str = ""
    pages_scraped: int = 0

    def to_dict(self) -> Dict:
        return {
            "emails": self.emails,
            "phones": self.phones,
            "whatsapp": self.whatsapp,
            "social_links": self.social_links,
            "names": self.names,
            "addresses": self.addresses,
            "source_url": self.source_url,
            "pages_scraped": self.pages_scraped
        }


def validate_url(url: str) -> Tuple[Optional[str], Optional[str]]:
    """Validate and normalize URL. Returns (normalized_url, error)."""
    if not url or not isinstance(url, str):
        return None, "URL is required"

    url = url.strip()[:2000]  # Limit length

    # Remove control characters
    url = re.sub(r'[\x00-\x1f\x7f]', '', url)

    # Add protocol if missing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    try:
        parsed = urlparse(url)
        if not parsed.netloc or len(parsed.netloc) < 3:
            return None, "Invalid URL format"

        # Block local/private IPs
        hostname = parsed.netloc.lower().split(':')[0]
        blocked_hosts = {'localhost', '127.0.0.1', '0.0.0.0', '::1', '[::1]'}
        if hostname in blocked_hosts:
            return None, "Local URLs not allowed"

        # Block private IP ranges
        if hostname.startswith(('192.168.', '10.', '172.16.', '172.17.', '172.18.',
                                '172.19.', '172.20.', '172.21.', '172.22.', '172.23.',
                                '172.24.', '172.25.', '172.26.', '172.27.', '172.28.',
                                '172.29.', '172.30.', '172.31.')):
            return None, "Private IP addresses not allowed"

        return url, None
    except Exception as e:
        return None, f"Invalid URL: {str(e)[:50]}"


class WebScraper:
    """
    Multi-strategy web scraper that handles static and dynamic sites.
    """

    # Pages to prioritize for contact info
    PRIORITY_PATHS = [
        '/contact', '/contact-us', '/contactus', '/contact.html',
        '/about', '/about-us', '/aboutus', '/about.html',
        '/team', '/our-team', '/staff',
        '/support', '/help',
        '/imprint', '/impressum',  # German legal page
        '/legal', '/privacy',
        '/',  # Homepage
    ]

    # Paths to avoid
    SKIP_PATHS = [
        '/blog', '/news', '/articles', '/posts',
        '/products', '/shop', '/store', '/cart', '/checkout',
        '/login', '/signin', '/register', '/signup', '/auth',
        '/search', '/tag', '/category', '/archive',
        '/wp-content', '/wp-includes', '/wp-admin', '/wp-json',
        '/static', '/assets', '/images', '/css', '/js', '/fonts',
        '/api/', '/feed', '/rss', '/sitemap',
    ]

    # File extensions to skip
    SKIP_EXTENSIONS = {
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        '.zip', '.rar', '.tar', '.gz', '.7z',
        '.exe', '.dmg', '.pkg', '.msi', '.deb', '.rpm',
        '.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', '.ico', '.bmp',
        '.mp3', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm',
        '.css', '.js', '.json', '.xml', '.woff', '.woff2', '.ttf', '.eot',
    }

    def __init__(self, max_pages: int = MAX_PAGES_DEFAULT, timeout: int = DEFAULT_TIMEOUT):
        self.max_pages = min(max_pages, 50)  # Hard cap
        self.timeout = min(timeout, 60)  # Hard cap
        self.visited_urls: Set[str] = set()
        self.use_playwright = False

        # User agent
        if HAS_FAKE_UA:
            try:
                self.ua = UserAgent(browsers=['chrome', 'firefox', 'edge'])
            except Exception:
                self.ua = None
        else:
            self.ua = None

    def _get_user_agent(self) -> str:
        """Get a user agent string."""
        if self.ua:
            try:
                return self.ua.random
            except Exception:
                pass
        return 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

    def _get_headers(self) -> Dict[str, str]:
        """Generate realistic browser headers."""
        return {
            'User-Agent': self._get_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        }

    def _normalize_url(self, url: str) -> str:
        """Normalize and validate URL."""
        url = url.strip()
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        # Remove fragment
        url, _ = urldefrag(url)

        # Remove trailing slash for consistency
        return url.rstrip('/')

    def _get_base_domain(self, url: str) -> str:
        """Extract base domain from URL."""
        if HAS_TLDEXTRACT:
            try:
                extracted = tldextract.extract(url)
                return f"{extracted.domain}.{extracted.suffix}"
            except Exception:
                pass

        # Fallback
        try:
            parsed = urlparse(url)
            parts = parsed.netloc.split('.')
            if len(parts) >= 2:
                return '.'.join(parts[-2:])
            return parsed.netloc
        except Exception:
            return ""

    def _is_same_domain(self, url: str, base_url: str) -> bool:
        """Check if URL belongs to same domain."""
        return self._get_base_domain(url) == self._get_base_domain(base_url)

    def _should_skip_url(self, url: str) -> bool:
        """Check if URL should be skipped."""
        try:
            parsed = urlparse(url.lower())
            path = parsed.path

            # Check extensions
            for ext in self.SKIP_EXTENSIONS:
                if path.endswith(ext):
                    return True

            # Check paths
            for skip_path in self.SKIP_PATHS:
                if skip_path in path:
                    return True

            return False
        except Exception:
            return True

    def _extract_links(self, html: str, base_url: str) -> List[str]:
        """Extract and filter relevant links from HTML."""
        try:
            soup = BeautifulSoup(html[:MAX_RESPONSE_SIZE], 'lxml')
        except Exception:
            try:
                soup = BeautifulSoup(html[:MAX_RESPONSE_SIZE], 'html.parser')
            except Exception:
                return []

        links = []
        seen = set()

        for a_tag in soup.find_all('a', href=True, limit=100):  # Limit tags to parse
            try:
                href = a_tag['href'].strip()[:500]  # Limit href length

                # Skip anchors, javascript, mailto, tel
                if href.startswith(('#', 'javascript:', 'mailto:', 'tel:', 'data:')):
                    continue

                # Resolve relative URLs
                full_url = urljoin(base_url, href)
                full_url = self._normalize_url(full_url)

                # Only same domain links
                if not self._is_same_domain(full_url, base_url):
                    continue

                if self._should_skip_url(full_url):
                    continue

                if full_url not in self.visited_urls and full_url not in seen:
                    seen.add(full_url)
                    links.append(full_url)

                if len(links) >= 50:  # Limit links per page
                    break

            except Exception:
                continue

        return links

    def _prioritize_urls(self, urls: List[str], base_url: str) -> List[str]:
        """Prioritize URLs based on likelihood of containing contact info."""
        priority_urls = []
        other_urls = []

        try:
            parsed_base = urlparse(base_url)
            base_origin = f"{parsed_base.scheme}://{parsed_base.netloc}"
        except Exception:
            base_origin = base_url

        # Add priority paths
        for path in self.PRIORITY_PATHS:
            try:
                priority_url = self._normalize_url(base_origin + path)
                if priority_url not in self.visited_urls and priority_url not in priority_urls:
                    priority_urls.append(priority_url)
            except Exception:
                continue

        # Categorize found URLs
        for url in urls:
            try:
                parsed = urlparse(url)
                path = parsed.path.lower()

                is_priority = any(p in path for p in [
                    'contact', 'about', 'team', 'support', 'imprint', 'impressum'
                ])

                if is_priority and url not in priority_urls:
                    priority_urls.append(url)
                elif url not in priority_urls and url not in other_urls:
                    other_urls.append(url)
            except Exception:
                continue

        return priority_urls[:20] + other_urls[:20]  # Limit total URLs

    async def _fetch_static(self, url: str) -> ScrapedPage:
        """Fetch page using httpx (static scraping)."""
        errors = []

        # Try with SSL verification first, then without
        for verify in [True, False]:
            try:
                async with httpx.AsyncClient(
                    follow_redirects=True,
                    max_redirects=MAX_REDIRECTS,
                    timeout=httpx.Timeout(self.timeout, connect=10.0),
                    verify=verify,
                    limits=httpx.Limits(max_connections=10)
                ) as client:
                    response = await client.get(url, headers=self._get_headers())

                    if response.status_code != 200:
                        errors.append(f"HTTP {response.status_code}")
                        if response.status_code in [403, 401, 429]:
                            return ScrapedPage(
                                url=url,
                                html="",
                                text="",
                                status=response.status_code,
                                error=f"Access denied (HTTP {response.status_code})"
                            )
                        continue

                    # Check content type
                    content_type = response.headers.get('content-type', '')
                    if 'text/html' not in content_type and 'text/plain' not in content_type:
                        if any(t in content_type for t in ['image', 'pdf', 'video', 'audio']):
                            return ScrapedPage(
                                url=url,
                                html="",
                                text="",
                                error="Not an HTML page"
                            )

                    # Read with size limit
                    html = response.text[:MAX_RESPONSE_SIZE]

                    try:
                        soup = BeautifulSoup(html, 'lxml')
                    except Exception:
                        soup = BeautifulSoup(html, 'html.parser')

                    # Remove script and style elements
                    for tag in soup(['script', 'style', 'noscript', 'iframe', 'svg']):
                        tag.decompose()

                    text = soup.get_text(separator=' ', strip=True)[:MAX_RESPONSE_SIZE]
                    title = soup.title.string if soup.title else ""

                    return ScrapedPage(
                        url=str(response.url),
                        html=html,
                        text=text,
                        title=title[:200] if title else "",
                        status=response.status_code
                    )

            except httpx.TimeoutException:
                errors.append("Timeout")
            except httpx.ConnectError:
                errors.append("Connection failed")
            except httpx.TooManyRedirects:
                errors.append("Too many redirects")
            except Exception as e:
                errors.append(str(e)[:50])

        return ScrapedPage(
            url=url,
            html="",
            text="",
            error=f"Failed: {'; '.join(set(errors)[:3])}"
        )

    async def _fetch_dynamic(self, url: str) -> ScrapedPage:
        """Fetch page using Playwright (dynamic/JS-rendered content)."""
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
                )

                context = await browser.new_context(
                    user_agent=self._get_user_agent(),
                    viewport={'width': 1920, 'height': 1080}
                )

                page = await context.new_page()

                # Navigate with timeout
                await page.goto(url, wait_until='domcontentloaded', timeout=self.timeout * 1000)

                # Brief wait for JS to execute
                await asyncio.sleep(1)

                html = await page.content()
                title = await page.title()

                await browser.close()

                # Limit size
                html = html[:MAX_RESPONSE_SIZE]

                try:
                    soup = BeautifulSoup(html, 'lxml')
                except Exception:
                    soup = BeautifulSoup(html, 'html.parser')

                for tag in soup(['script', 'style', 'noscript', 'iframe', 'svg']):
                    tag.decompose()
                text = soup.get_text(separator=' ', strip=True)[:MAX_RESPONSE_SIZE]

                return ScrapedPage(
                    url=url,
                    html=html,
                    text=text,
                    title=title[:200] if title else "",
                    status=200
                )

        except ImportError:
            return ScrapedPage(
                url=url,
                html="",
                text="",
                error="Playwright not installed"
            )
        except Exception as e:
            return ScrapedPage(
                url=url,
                html="",
                text="",
                error=f"Dynamic scrape failed: {str(e)[:50]}"
            )

    async def _fetch_page(self, url: str) -> ScrapedPage:
        """Fetch page using appropriate method."""
        # Try static first
        page = await self._fetch_static(url)

        # If static works and has reasonable content, use it
        if page.html and len(page.text) > 100:
            return page

        # If static failed or minimal content, try dynamic
        if self.use_playwright:
            dynamic_page = await self._fetch_dynamic(url)
            if dynamic_page.html and len(dynamic_page.text) > len(page.text):
                return dynamic_page

        return page

    def _extract_contacts_from_page(self, page: ScrapedPage) -> ContactData:
        """Extract all contact information from a scraped page."""
        contacts = ContactData(source_url=page.url)

        if not page.html and not page.text:
            return contacts

        try:
            # Extract all types of contact info
            contacts.emails = list(EmailExtractor.extract(page.text, page.html))
            contacts.phones = PhoneExtractor.extract(page.text)
            contacts.whatsapp = WhatsAppExtractor.extract(page.text, page.html)
            contacts.social_links = SocialLinkExtractor.extract(page.text, page.html)
            contacts.names = NameExtractor.extract(page.text, page.html)
            contacts.addresses = AddressExtractor.extract(page.text)
        except Exception as e:
            logger.warning(f"Extraction error on {page.url}: {e}")

        return contacts

    def _merge_contacts(self, all_contacts: List[ContactData]) -> ContactData:
        """Merge contact data from multiple pages."""
        merged = ContactData()

        emails = set()
        phones_seen = set()
        whatsapp_seen = set()
        names = set()
        addresses = set()
        social_links: Dict[str, Dict[str, Dict]] = {}

        for contacts in all_contacts:
            # Emails
            for email in contacts.emails:
                emails.add(email)

            # Phones (dedupe by e164)
            for phone in contacts.phones:
                key = phone.get('e164', phone.get('original', ''))
                if key and key not in phones_seen:
                    phones_seen.add(key)
                    merged.phones.append(phone)

            # WhatsApp (dedupe by number)
            for wa in contacts.whatsapp:
                num = wa.get('number', '')
                if num and num not in whatsapp_seen:
                    whatsapp_seen.add(num)
                    merged.whatsapp.append(wa)

            # Social links
            for platform, links in contacts.social_links.items():
                if platform not in social_links:
                    social_links[platform] = {}
                for link in links:
                    username = link.get('username', '')
                    if username and username not in social_links[platform]:
                        social_links[platform][username] = link

            # Names
            for name in contacts.names:
                names.add(name)

            # Addresses
            for addr in contacts.addresses:
                addresses.add(addr)

        merged.emails = sorted(list(emails))[:50]
        merged.phones = merged.phones[:30]
        merged.whatsapp = merged.whatsapp[:20]
        merged.names = list(names)[:10]
        merged.addresses = list(addresses)[:5]
        merged.social_links = {
            platform: list(links.values())[:20]
            for platform, links in social_links.items()
        }

        return merged

    async def scrape(self, url: str, use_dynamic: bool = False) -> ContactData:
        """
        Main scraping method - crawls website and extracts contacts.

        Args:
            url: The website URL to scrape
            use_dynamic: Whether to use Playwright for JS-rendered sites
        """
        self.use_playwright = use_dynamic
        self.visited_urls = set()

        # Validate URL
        normalized_url, error = validate_url(url)
        if error:
            return ContactData(source_url=url, pages_scraped=0)

        base_url = self._normalize_url(normalized_url)
        all_contacts: List[ContactData] = []
        urls_to_visit = [base_url]

        # Get initial page
        initial_page = await self._fetch_page(base_url)
        if initial_page.html:
            self.visited_urls.add(base_url)
            all_contacts.append(self._extract_contacts_from_page(initial_page))

            # Get all links and prioritize them
            found_links = self._extract_links(initial_page.html, base_url)
            urls_to_visit = self._prioritize_urls(found_links, base_url)

        # Scrape additional pages
        pages_scraped = 1

        for url in urls_to_visit:
            if pages_scraped >= self.max_pages:
                break

            if url in self.visited_urls:
                continue

            self.visited_urls.add(url)

            try:
                page = await self._fetch_page(url)

                if page.html:
                    contacts = self._extract_contacts_from_page(page)
                    all_contacts.append(contacts)
                    pages_scraped += 1

            except Exception as e:
                logger.warning(f"Failed to scrape {url}: {e}")
                continue

        # Merge all contacts
        merged = self._merge_contacts(all_contacts)
        merged.source_url = base_url
        merged.pages_scraped = pages_scraped

        return merged


async def extract_contacts(
    url: str,
    max_pages: int = 10,
    use_dynamic: bool = False,
    timeout: int = 30
) -> Dict:
    """
    Main entry point for contact extraction.

    Args:
        url: Website URL to extract contacts from
        max_pages: Maximum pages to crawl
        use_dynamic: Use Playwright for JS-rendered sites
        timeout: Request timeout in seconds

    Returns:
        Dictionary with extracted contact information
    """
    scraper = WebScraper(max_pages=max_pages, timeout=timeout)
    contacts = await scraper.scrape(url, use_dynamic=use_dynamic)
    return contacts.to_dict()
