from http.server import BaseHTTPRequestHandler
import json
import re
import urllib.request
import urllib.error
import ssl
from urllib.parse import urlparse, urljoin
from html.parser import HTMLParser

# Disable SSL verification for problematic sites
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

class LinkExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.text_content = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            for attr, value in attrs:
                if attr == 'href' and value:
                    self.links.append(value)

    def handle_data(self, data):
        self.text_content.append(data)

def fetch_url(url, timeout=15):
    """Fetch URL content"""
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }

    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl_context) as response:
            content = response.read().decode('utf-8', errors='ignore')
            return content, response.geturl()
    except Exception as e:
        # Try http if https fails
        if url.startswith('https://'):
            try:
                http_url = url.replace('https://', 'http://')
                req = urllib.request.Request(http_url, headers=headers)
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    content = response.read().decode('utf-8', errors='ignore')
                    return content, response.geturl()
            except:
                pass
        raise e

def extract_emails(html, text):
    """Extract email addresses"""
    emails = set()

    # Standard email pattern
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

    # Find in HTML
    for match in re.finditer(email_pattern, html):
        email = match.group().lower().strip('.')
        if not any(x in email for x in ['example.com', 'yourdomain', 'email.com', '.png', '.jpg', '.gif', '.css', '.js']):
            emails.add(email)

    # Find obfuscated emails
    obfuscated_patterns = [
        r'([a-zA-Z0-9._%+-]+)\s*[\[\(]\s*at\s*[\]\)]\s*([a-zA-Z0-9.-]+)\s*[\[\(]\s*dot\s*[\]\)]\s*([a-zA-Z]{2,})',
        r'([a-zA-Z0-9._%+-]+)\s*@\s*([a-zA-Z0-9.-]+)\s*\.\s*([a-zA-Z]{2,})',
    ]

    for pattern in obfuscated_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            try:
                email = f"{match.group(1)}@{match.group(2)}.{match.group(3)}".lower()
                emails.add(email)
            except:
                pass

    # Find mailto links
    mailto_pattern = r'mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
    for match in re.finditer(mailto_pattern, html, re.IGNORECASE):
        emails.add(match.group(1).lower())

    return list(emails)

def extract_phones(html, text):
    """Extract phone numbers"""
    phones = []
    seen = set()

    # Phone patterns
    patterns = [
        r'\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
        r'\+\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}',
        r'\(\d{3}\)\s*\d{3}[-.\s]?\d{4}',
        r'\d{3}[-.\s]\d{3}[-.\s]\d{4}',
    ]

    combined = html + ' ' + text

    for pattern in patterns:
        for match in re.finditer(pattern, combined):
            phone = match.group()
            digits = re.sub(r'\D', '', phone)

            if 7 <= len(digits) <= 15 and digits not in seen:
                seen.add(digits)
                phones.append({
                    'original': phone.strip(),
                    'digits': digits,
                    'formatted': phone.strip()
                })

    return phones[:20]  # Limit results

def extract_whatsapp(html):
    """Extract WhatsApp links"""
    whatsapp = []
    seen = set()

    patterns = [
        r'https?://(?:api\.)?whatsapp\.com/send\?phone=(\d+)',
        r'https?://wa\.me/(\d+)',
        r'https?://web\.whatsapp\.com/send\?phone=(\d+)',
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, html, re.IGNORECASE):
            number = match.group(1)
            if number not in seen:
                seen.add(number)
                whatsapp.append({
                    'number': number,
                    'link': f'https://wa.me/{number}'
                })

    return whatsapp

def extract_social_links(html, links):
    """Extract social media links"""
    social = {
        'facebook': [],
        'twitter': [],
        'linkedin': [],
        'instagram': [],
        'youtube': [],
        'tiktok': [],
        'github': [],
        'telegram': [],
        'pinterest': []
    }

    patterns = {
        'facebook': r'(?:https?://)?(?:www\.)?facebook\.com/([a-zA-Z0-9._-]+)',
        'twitter': r'(?:https?://)?(?:www\.)?(?:twitter|x)\.com/([a-zA-Z0-9_]+)',
        'linkedin': r'(?:https?://)?(?:www\.)?linkedin\.com/(?:in|company)/([a-zA-Z0-9_-]+)',
        'instagram': r'(?:https?://)?(?:www\.)?instagram\.com/([a-zA-Z0-9._]+)',
        'youtube': r'(?:https?://)?(?:www\.)?youtube\.com/(?:@|channel/|user/)?([a-zA-Z0-9_-]+)',
        'tiktok': r'(?:https?://)?(?:www\.)?tiktok\.com/@([a-zA-Z0-9._]+)',
        'github': r'(?:https?://)?(?:www\.)?github\.com/([a-zA-Z0-9_-]+)',
        'telegram': r'(?:https?://)?(?:www\.)?t\.me/([a-zA-Z0-9_]+)',
        'pinterest': r'(?:https?://)?(?:www\.)?pinterest\.com/([a-zA-Z0-9_]+)',
    }

    seen = {platform: set() for platform in social}
    combined = html + ' ' + ' '.join(links)

    for platform, pattern in patterns.items():
        for match in re.finditer(pattern, combined, re.IGNORECASE):
            username = match.group(1)
            # Skip common non-profile paths
            if username.lower() in ['share', 'sharer', 'intent', 'watch', 'search', 'explore', 'login', 'signup', 'help', 'about', 'privacy', 'terms']:
                continue
            if username not in seen[platform]:
                seen[platform].add(username)
                social[platform].append({
                    'username': username,
                    'url': match.group(0) if match.group(0).startswith('http') else f'https://{match.group(0)}',
                    'platform': platform
                })

    return social

def crawl_website(start_url, max_pages=5):
    """Crawl website and extract contacts"""
    all_emails = set()
    all_phones = []
    all_whatsapp = []
    all_social = {
        'facebook': [], 'twitter': [], 'linkedin': [], 'instagram': [],
        'youtube': [], 'tiktok': [], 'github': [], 'telegram': [], 'pinterest': []
    }

    parsed_start = urlparse(start_url if start_url.startswith('http') else f'https://{start_url}')
    base_domain = parsed_start.netloc or parsed_start.path.split('/')[0]

    visited = set()
    to_visit = [start_url if start_url.startswith('http') else f'https://{start_url}']
    pages_crawled = 0

    # Priority pages to check
    priority_paths = ['/contact', '/about', '/contact-us', '/about-us', '/team', '/support']

    while to_visit and pages_crawled < max_pages:
        url = to_visit.pop(0)

        if url in visited:
            continue

        visited.add(url)

        try:
            html, final_url = fetch_url(url)
            pages_crawled += 1

            # Parse HTML
            parser = LinkExtractor()
            try:
                parser.feed(html)
            except:
                pass

            text = ' '.join(parser.text_content)

            # Extract data
            emails = extract_emails(html, text)
            all_emails.update(emails)

            phones = extract_phones(html, text)
            for phone in phones:
                if phone['digits'] not in [p['digits'] for p in all_phones]:
                    all_phones.append(phone)

            whatsapp = extract_whatsapp(html)
            for wa in whatsapp:
                if wa['number'] not in [w['number'] for w in all_whatsapp]:
                    all_whatsapp.append(wa)

            social = extract_social_links(html, parser.links)
            for platform, links in social.items():
                for link in links:
                    if link['username'] not in [l['username'] for l in all_social[platform]]:
                        all_social[platform].append(link)

            # Find more pages to crawl (priority pages first)
            if pages_crawled < max_pages:
                for link in parser.links:
                    try:
                        full_url = urljoin(final_url, link)
                        parsed = urlparse(full_url)

                        # Only follow links on same domain
                        if base_domain in parsed.netloc and full_url not in visited:
                            # Prioritize contact/about pages
                            if any(p in parsed.path.lower() for p in priority_paths):
                                to_visit.insert(0, full_url)
                            elif len(to_visit) < 20:
                                to_visit.append(full_url)
                    except:
                        pass

        except Exception as e:
            print(f"Error crawling {url}: {e}")
            continue

    return {
        'success': True,
        'source_url': start_url,
        'pages_scraped': pages_crawled,
        'emails': list(all_emails),
        'phones': all_phones[:15],
        'whatsapp': all_whatsapp,
        'social_links': all_social
    }

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body) if body else {}

            url = data.get('url', '')
            max_pages = min(int(data.get('max_pages', 5)), 10)

            if not url:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'URL is required'}).encode())
                return

            result = crawl_website(url, max_pages)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e), 'success': False}).encode())

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'ok', 'message': 'Contact Extractor API - Use POST to extract contacts'}).encode())
