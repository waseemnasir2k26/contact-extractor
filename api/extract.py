from http.server import BaseHTTPRequestHandler
import json
import re
import urllib.request
import urllib.error
import ssl
import socket
from urllib.parse import urlparse, urljoin
from html.parser import HTMLParser
import time

# Set socket timeout globally
socket.setdefaulttimeout(8)

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

def fetch_url(url, timeout=6):
    """Fetch URL content with strict timeout"""
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }

    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl_context) as response:
            # Limit content size to 500KB for speed
            content = response.read(500000).decode('utf-8', errors='ignore')
            return content, response.geturl()
    except Exception as e:
        if url.startswith('https://'):
            try:
                http_url = url.replace('https://', 'http://')
                req = urllib.request.Request(http_url, headers=headers)
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    content = response.read(500000).decode('utf-8', errors='ignore')
                    return content, response.geturl()
            except:
                pass
        raise e

def extract_emails(html, text):
    """Extract email addresses"""
    emails = set()
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

    for match in re.finditer(email_pattern, html):
        email = match.group().lower().strip('.')
        if not any(x in email for x in ['example.com', 'yourdomain', 'email.com', '.png', '.jpg', '.gif', '.css', '.js', 'wixpress', 'sentry']):
            emails.add(email)

    # Mailto links
    for match in re.finditer(r'mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', html, re.IGNORECASE):
        emails.add(match.group(1).lower())

    return list(emails)[:20]

def extract_phones(html):
    """Extract phone numbers"""
    phones = []
    seen = set()

    patterns = [
        r'\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
        r'\+\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}',
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, html):
            phone = match.group()
            digits = re.sub(r'\D', '', phone)
            if 10 <= len(digits) <= 15 and digits not in seen:
                seen.add(digits)
                phones.append({'original': phone.strip(), 'digits': digits, 'formatted': phone.strip()})
                if len(phones) >= 10:
                    return phones

    return phones

def extract_whatsapp(html):
    """Extract WhatsApp links"""
    whatsapp = []
    seen = set()

    for match in re.finditer(r'(?:api\.)?whatsapp\.com/send\?phone=(\d+)|wa\.me/(\d+)', html, re.IGNORECASE):
        number = match.group(1) or match.group(2)
        if number and number not in seen:
            seen.add(number)
            whatsapp.append({'number': number, 'link': f'https://wa.me/{number}'})

    return whatsapp[:5]

def extract_social_links(html):
    """Extract social media links"""
    social = {}

    patterns = {
        'facebook': r'facebook\.com/([a-zA-Z0-9._-]+)',
        'twitter': r'(?:twitter|x)\.com/([a-zA-Z0-9_]+)',
        'linkedin': r'linkedin\.com/(?:in|company)/([a-zA-Z0-9_-]+)',
        'instagram': r'instagram\.com/([a-zA-Z0-9._]+)',
        'youtube': r'youtube\.com/(?:@|channel/|user/)?([a-zA-Z0-9_-]+)',
        'tiktok': r'tiktok\.com/@([a-zA-Z0-9._]+)',
        'github': r'github\.com/([a-zA-Z0-9_-]+)',
        'telegram': r't\.me/([a-zA-Z0-9_]+)',
    }

    skip = ['share', 'sharer', 'intent', 'watch', 'search', 'login', 'signup', 'help', 'about', 'privacy', 'terms', 'policy', 'plugins', 'dialog']

    for platform, pattern in patterns.items():
        social[platform] = []
        seen = set()
        for match in re.finditer(pattern, html, re.IGNORECASE):
            username = match.group(1)
            if username.lower() not in skip and username not in seen and len(username) > 1:
                seen.add(username)
                social[platform].append({
                    'username': username,
                    'url': f'https://{platform}.com/{username}' if platform != 'telegram' else f'https://t.me/{username}',
                    'platform': platform
                })
                if len(social[platform]) >= 3:
                    break

    return social

def crawl_website(start_url, max_pages=3, timeout_seconds=25):
    """Crawl website with strict time limit"""
    start_time = time.time()

    all_emails = set()
    all_phones = []
    all_whatsapp = []
    all_social = {}

    if not start_url.startswith('http'):
        start_url = 'https://' + start_url

    parsed_start = urlparse(start_url)
    base_domain = parsed_start.netloc

    visited = set()
    to_visit = [start_url]
    pages_crawled = 0

    # Priority pages
    priority_keywords = ['contact', 'about', 'team', 'support', 'reach']

    while to_visit and pages_crawled < max_pages:
        # Check time limit
        if time.time() - start_time > timeout_seconds:
            break

        url = to_visit.pop(0)
        if url in visited:
            continue

        visited.add(url)

        try:
            html, final_url = fetch_url(url, timeout=6)
            pages_crawled += 1

            # Parse
            parser = LinkExtractor()
            try:
                parser.feed(html)
            except:
                pass

            text = ' '.join(parser.text_content)

            # Extract
            emails = extract_emails(html, text)
            all_emails.update(emails)

            phones = extract_phones(html)
            for p in phones:
                if p['digits'] not in [x['digits'] for x in all_phones]:
                    all_phones.append(p)

            wa = extract_whatsapp(html)
            for w in wa:
                if w['number'] not in [x['number'] for x in all_whatsapp]:
                    all_whatsapp.append(w)

            social = extract_social_links(html)
            for platform, links in social.items():
                if platform not in all_social:
                    all_social[platform] = []
                for link in links:
                    if link['username'] not in [x['username'] for x in all_social[platform]]:
                        all_social[platform].append(link)

            # Find priority pages
            if pages_crawled < max_pages and time.time() - start_time < timeout_seconds - 5:
                for link in parser.links[:50]:
                    try:
                        full_url = urljoin(final_url, link)
                        parsed = urlparse(full_url)
                        if base_domain in parsed.netloc and full_url not in visited:
                            if any(kw in parsed.path.lower() for kw in priority_keywords):
                                to_visit.insert(0, full_url)
                                break
                    except:
                        pass

        except Exception as e:
            continue

    elapsed = round(time.time() - start_time, 1)

    return {
        'success': True,
        'source_url': start_url,
        'pages_scraped': pages_crawled,
        'time_taken': elapsed,
        'emails': list(all_emails),
        'phones': all_phones[:10],
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

            # Handle batch extraction
            urls = data.get('urls', [])
            if not urls:
                url = data.get('url', '')
                if url:
                    urls = [url]

            if not urls:
                self.send_error_response(400, 'URL is required')
                return

            # Limit to 5 URLs
            urls = urls[:5]
            max_pages = min(int(data.get('max_pages', 3)), 5)

            results = []
            for url in urls:
                try:
                    result = crawl_website(url.strip(), max_pages=max_pages, timeout_seconds=20)
                    results.append(result)
                except Exception as e:
                    results.append({
                        'success': False,
                        'source_url': url,
                        'error': str(e),
                        'emails': [],
                        'phones': [],
                        'whatsapp': [],
                        'social_links': {}
                    })

            # Return single result or array
            response = results[0] if len(results) == 1 else {'success': True, 'results': results}

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())

        except Exception as e:
            self.send_error_response(500, str(e))

    def send_error_response(self, code, message):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({'success': False, 'error': message}).encode())

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'ok', 'message': 'POST with {url} or {urls: [...]} to extract'}).encode())
