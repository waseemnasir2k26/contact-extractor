from http.server import BaseHTTPRequestHandler
import json
import re
import urllib.request
import ssl
import socket
from urllib.parse import urlparse, urljoin
from html.parser import HTMLParser
import time

socket.setdefaulttimeout(8)

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

class LinkExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.text = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            for attr, value in attrs:
                if attr == 'href' and value:
                    self.links.append(value)

    def handle_data(self, data):
        self.text.append(data)

def fetch_url(url, timeout=5):
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl_context) as resp:
            return resp.read(300000).decode('utf-8', errors='ignore'), resp.geturl()
    except:
        if url.startswith('https://'):
            try:
                req = urllib.request.Request(url.replace('https://', 'http://'), headers=headers)
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    return resp.read(300000).decode('utf-8', errors='ignore'), resp.geturl()
            except:
                pass
        raise

def extract_all(html):
    result = {'emails': [], 'phones': [], 'whatsapp': [], 'social_links': {}}

    # Emails
    skip = ['example.com', 'yourdomain', 'email.com', '.png', '.jpg', '.css', '.js', 'wixpress', 'sentry', 'wordpress']
    for m in re.finditer(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', html):
        email = m.group().lower().strip('.')
        if not any(s in email for s in skip) and email not in result['emails']:
            result['emails'].append(email)

    for m in re.finditer(r'mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', html, re.I):
        email = m.group(1).lower()
        if email not in result['emails']:
            result['emails'].append(email)

    # Phones
    seen_digits = set()
    for m in re.finditer(r'\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', html):
        phone = m.group()
        digits = re.sub(r'\D', '', phone)
        if 10 <= len(digits) <= 15 and digits not in seen_digits:
            seen_digits.add(digits)
            result['phones'].append({'original': phone.strip(), 'digits': digits, 'formatted': phone.strip()})

    # WhatsApp
    seen_wa = set()
    for m in re.finditer(r'(?:api\.)?whatsapp\.com/send\?phone=(\d+)|wa\.me/(\d+)', html, re.I):
        num = m.group(1) or m.group(2)
        if num and num not in seen_wa:
            seen_wa.add(num)
            result['whatsapp'].append({'number': num, 'link': f'https://wa.me/{num}'})

    # Social
    social_patterns = {
        'facebook': r'facebook\.com/([a-zA-Z0-9._-]+)',
        'twitter': r'(?:twitter|x)\.com/([a-zA-Z0-9_]+)',
        'linkedin': r'linkedin\.com/(?:in|company)/([a-zA-Z0-9_-]+)',
        'instagram': r'instagram\.com/([a-zA-Z0-9._]+)',
        'youtube': r'youtube\.com/(?:@|channel/|user/)?([a-zA-Z0-9_-]+)',
        'tiktok': r'tiktok\.com/@([a-zA-Z0-9._]+)',
        'github': r'github\.com/([a-zA-Z0-9_-]+)',
        'telegram': r't\.me/([a-zA-Z0-9_]+)',
    }

    skip_usernames = ['share', 'sharer', 'intent', 'watch', 'search', 'login', 'signup', 'help', 'about', 'privacy', 'terms', 'policy']

    for platform, pattern in social_patterns.items():
        result['social_links'][platform] = []
        seen = set()
        for m in re.finditer(pattern, html, re.I):
            username = m.group(1)
            if username.lower() not in skip_usernames and username not in seen and len(username) > 1:
                seen.add(username)
                url = f'https://t.me/{username}' if platform == 'telegram' else f'https://{platform}.com/{username}'
                result['social_links'][platform].append({'username': username, 'url': url, 'platform': platform})

    return result

def crawl(start_url, max_pages=2):
    start = time.time()

    if not start_url.startswith('http'):
        start_url = 'https://' + start_url

    base = urlparse(start_url).netloc
    visited = set()
    to_visit = [start_url]
    all_data = {'emails': [], 'phones': [], 'whatsapp': [], 'social_links': {}}
    pages = 0

    while to_visit and pages < max_pages and (time.time() - start) < 20:
        url = to_visit.pop(0)
        if url in visited:
            continue
        visited.add(url)

        try:
            html, final_url = fetch_url(url)
            pages += 1

            data = extract_all(html)

            for e in data['emails']:
                if e not in all_data['emails']:
                    all_data['emails'].append(e)

            for p in data['phones']:
                if p['digits'] not in [x['digits'] for x in all_data['phones']]:
                    all_data['phones'].append(p)

            for w in data['whatsapp']:
                if w['number'] not in [x['number'] for x in all_data['whatsapp']]:
                    all_data['whatsapp'].append(w)

            for platform, links in data['social_links'].items():
                if platform not in all_data['social_links']:
                    all_data['social_links'][platform] = []
                for link in links:
                    if link['username'] not in [x['username'] for x in all_data['social_links'][platform]]:
                        all_data['social_links'][platform].append(link)

            # Find contact page
            if pages < max_pages:
                parser = LinkExtractor()
                try:
                    parser.feed(html)
                except:
                    pass

                for link in parser.links[:30]:
                    try:
                        full = urljoin(final_url, link)
                        if base in urlparse(full).netloc and full not in visited:
                            if any(k in link.lower() for k in ['contact', 'about']):
                                to_visit.insert(0, full)
                                break
                    except:
                        pass
        except Exception as e:
            continue

    return {
        'success': True,
        'source_url': start_url,
        'pages_scraped': pages,
        'time_taken': round(time.time() - start, 1),
        'emails': all_data['emails'][:15],
        'phones': all_data['phones'][:10],
        'whatsapp': all_data['whatsapp'][:5],
        'social_links': all_data['social_links']
    }

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'ok', 'message': 'POST {url} to extract'}).encode())

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length).decode('utf-8')
            data = json.loads(body) if body else {}

            urls = data.get('urls', [])
            if not urls and data.get('url'):
                urls = [data.get('url')]

            if not urls:
                self._send_json(400, {'success': False, 'error': 'URL required'})
                return

            urls = [u.strip() for u in urls[:5] if u.strip()]
            max_pages = min(int(data.get('max_pages', 2)), 3)

            results = []
            for url in urls:
                try:
                    results.append(crawl(url, max_pages))
                except Exception as e:
                    results.append({'success': False, 'source_url': url, 'error': str(e), 'emails': [], 'phones': [], 'whatsapp': [], 'social_links': {}})

            resp = results[0] if len(results) == 1 else {'success': True, 'results': results}
            self._send_json(200, resp)

        except Exception as e:
            self._send_json(500, {'success': False, 'error': str(e)})

    def _send_json(self, code, data):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
