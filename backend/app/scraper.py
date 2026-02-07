"""
Web Scraper Module
Handles both static and dynamic (JavaScript-rendered) websites.
"""

import asyncio
import re
from typing import Dict, List, Set, Optional
from urllib.parse import urlparse, urljoin, urldefrag
from dataclasses import dataclass, field
from bs4 import BeautifulSoup
import httpx
from fake_useragent import UserAgent
import tldextract

from app.extractors import (
    EmailExtractor,
    PhoneExtractor,
    WhatsAppExtractor,
    SocialLinkExtractor,
    NameExtractor,
    AddressExtractor
)


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
        '/products', '/shop', '/store', '/cart',
        '/login', '/signin', '/register', '/signup',
        '/search', '/tag', '/category', '/archive',
        '/wp-content', '/wp-includes', '/wp-admin',
        '/static', '/assets', '/images', '/css', '/js',
    ]

    def __init__(self, max_pages: int = 10, timeout: int = 30):
        self.max_pages = max_pages
        self.timeout = timeout
        self.ua = UserAgent(browsers=['chrome', 'firefox', 'edge'])
        self.visited_urls: Set[str] = set()
        self.use_playwright = False

    def _get_headers(self) -> Dict[str, str]:
        """Generate realistic browser headers."""
        return {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
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
        extracted = tldextract.extract(url)
        return f"{extracted.domain}.{extracted.suffix}"

    def _is_same_domain(self, url: str, base_url: str) -> bool:
        """Check if URL belongs to same domain."""
        return self._get_base_domain(url) == self._get_base_domain(base_url)

    def _should_skip_url(self, url: str) -> bool:
        """Check if URL should be skipped."""
        parsed = urlparse(url.lower())
        path = parsed.path

        # Skip non-HTML resources
        if re.search(r'\.(pdf|doc|docx|xls|xlsx|zip|rar|exe|dmg|pkg|jpg|jpeg|png|gif|svg|mp3|mp4|avi|mov|css|js|json|xml|ico|woff|woff2|ttf|eot)$', path, re.IGNORECASE):
            return True

        # Skip certain paths
        for skip_path in self.SKIP_PATHS:
            if skip_path in path:
                return True

        return False

    def _extract_links(self, html: str, base_url: str) -> List[str]:
        """Extract and filter relevant links from HTML."""
        soup = BeautifulSoup(html, 'lxml')
        links = []

        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href'].strip()

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

            if full_url not in self.visited_urls:
                links.append(full_url)

        return links

    def _prioritize_urls(self, urls: List[str], base_url: str) -> List[str]:
        """Prioritize URLs based on likelihood of containing contact info."""
        priority_urls = []
        other_urls = []

        parsed_base = urlparse(base_url)
        base_origin = f"{parsed_base.scheme}://{parsed_base.netloc}"

        # Add priority paths
        for path in self.PRIORITY_PATHS:
            priority_url = self._normalize_url(base_origin + path)
            if priority_url not in self.visited_urls:
                priority_urls.append(priority_url)

        # Categorize found URLs
        for url in urls:
            parsed = urlparse(url)
            path = parsed.path.lower()

            is_priority = any(p in path for p in [
                'contact', 'about', 'team', 'support', 'imprint', 'impressum'
            ])

            if is_priority and url not in priority_urls:
                priority_urls.append(url)
            elif url not in priority_urls:
                other_urls.append(url)

        return priority_urls + other_urls

    async def _fetch_static(self, url: str) -> ScrapedPage:
        """Fetch page using httpx (static scraping)."""
        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=self.timeout,
                verify=False  # Handle SSL issues
            ) as client:
                response = await client.get(url, headers=self._get_headers())

                if response.status_code != 200:
                    return ScrapedPage(
                        url=url,
                        html="",
                        text="",
                        status=response.status_code,
                        error=f"HTTP {response.status_code}"
                    )

                html = response.text
                soup = BeautifulSoup(html, 'lxml')

                # Remove script and style elements
                for tag in soup(['script', 'style', 'noscript', 'iframe']):
                    tag.decompose()

                text = soup.get_text(separator=' ', strip=True)
                title = soup.title.string if soup.title else ""

                return ScrapedPage(
                    url=url,
                    html=html,
                    text=text,
                    title=title,
                    status=response.status_code
                )

        except Exception as e:
            return ScrapedPage(
                url=url,
                html="",
                text="",
                error=str(e)
            )

    async def _fetch_dynamic(self, url: str) -> ScrapedPage:
        """Fetch page using Playwright (dynamic/JS-rendered content)."""
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-setuid-sandbox']
                )
                page = await browser.new_page()

                # Set user agent
                await page.set_extra_http_headers(self._get_headers())

                await page.goto(url, wait_until='networkidle', timeout=self.timeout * 1000)

                # Wait for content to render
                await asyncio.sleep(2)

                html = await page.content()
                title = await page.title()

                await browser.close()

                soup = BeautifulSoup(html, 'lxml')
                for tag in soup(['script', 'style', 'noscript', 'iframe']):
                    tag.decompose()
                text = soup.get_text(separator=' ', strip=True)

                return ScrapedPage(
                    url=url,
                    html=html,
                    text=text,
                    title=title,
                    status=200
                )

        except Exception as e:
            return ScrapedPage(
                url=url,
                html="",
                text="",
                error=f"Dynamic scrape failed: {str(e)}"
            )

    async def _fetch_page(self, url: str) -> ScrapedPage:
        """Fetch page using appropriate method."""
        # Try static first
        page = await self._fetch_static(url)

        # If static works and has reasonable content, use it
        if page.html and len(page.text) > 200:
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

        # Extract all types of contact info
        contacts.emails = list(EmailExtractor.extract(page.text, page.html))
        contacts.phones = PhoneExtractor.extract(page.text)
        contacts.whatsapp = WhatsAppExtractor.extract(page.text, page.html)
        contacts.social_links = SocialLinkExtractor.extract(page.text, page.html)
        contacts.names = NameExtractor.extract(page.text, page.html)
        contacts.addresses = AddressExtractor.extract(page.text)

        return contacts

    def _merge_contacts(self, all_contacts: List[ContactData]) -> ContactData:
        """Merge contact data from multiple pages."""
        merged = ContactData()

        emails = set()
        phones_seen = set()
        whatsapp_seen = set()
        names = set()
        addresses = set()
        social_links = {}

        for contacts in all_contacts:
            # Emails
            for email in contacts.emails:
                emails.add(email)

            # Phones (dedupe by e164)
            for phone in contacts.phones:
                key = phone.get('e164', phone.get('original'))
                if key not in phones_seen:
                    phones_seen.add(key)
                    merged.phones.append(phone)

            # WhatsApp (dedupe by number)
            for wa in contacts.whatsapp:
                if wa['number'] not in whatsapp_seen:
                    whatsapp_seen.add(wa['number'])
                    merged.whatsapp.append(wa)

            # Social links
            for platform, links in contacts.social_links.items():
                if platform not in social_links:
                    social_links[platform] = {}
                for link in links:
                    username = link['username']
                    if username not in social_links[platform]:
                        social_links[platform][username] = link

            # Names
            for name in contacts.names:
                names.add(name)

            # Addresses
            for addr in contacts.addresses:
                addresses.add(addr)

        merged.emails = sorted(list(emails))
        merged.names = list(names)[:10]
        merged.addresses = list(addresses)[:5]
        merged.social_links = {
            platform: list(links.values())
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

        base_url = self._normalize_url(url)
        all_contacts: List[ContactData] = []
        urls_to_visit = [base_url]

        # Get priority URLs
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
            page = await self._fetch_page(url)

            if page.html:
                contacts = self._extract_contacts_from_page(page)
                all_contacts.append(contacts)
                pages_scraped += 1

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
