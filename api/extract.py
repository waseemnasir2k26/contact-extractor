"""
Contact Extractor - Vercel Serverless API
Extracts emails, phones, WhatsApp links, and social media profiles from websites.

Fixed issues:
- Hard timeout enforcement with signal-based abort
- Input validation and sanitization
- Safe regex patterns (no catastrophic backtracking)
- Proper error handling
- Response size limits
- SSL handling with fallback
"""

from http.server import BaseHTTPRequestHandler
import json
import re
import urllib.request
import urllib.error
import ssl
import signal
from urllib.parse import urlparse, urljoin, unquote
from html.parser import HTMLParser
import time
from contextlib import contextmanager

# Constants
MAX_RESPONSE_SIZE = 200000  # 200KB per page
MAX_PAGES = 3
MAX_URLS = 5
FETCH_TIMEOUT = 6  # Per-request timeout
TOTAL_TIMEOUT = 9  # Total execution timeout (Vercel hobby has 10s limit)
MAX_INPUT_LENGTH = 500000  # 500KB max text to process with regex


class TimeoutError(Exception):
    """Custom timeout exception."""
    pass


@contextmanager
def timeout_context(seconds):
    """Context manager for timeout - works on Unix systems."""
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Operation timed out after {seconds} seconds")

    # Only use signal on Unix (Vercel runs Linux)
    try:
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(seconds)
        try:
            yield
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
    except (ValueError, AttributeError):
        # signal.SIGALRM not available (Windows), just yield without timeout
        yield


class LinkExtractor(HTMLParser):
    """Safe HTML parser for link extraction."""

    def __init__(self):
        super().__init__()
        self.links = []
        self.text_chunks = []
        self._max_links = 50
        self._max_text = 100000
        self._text_len = 0

    def handle_starttag(self, tag, attrs):
        if tag == 'a' and len(self.links) < self._max_links:
            for attr, value in attrs:
                if attr == 'href' and value:
                    self.links.append(value[:500])  # Limit URL length
                    break

    def handle_data(self, data):
        if self._text_len < self._max_text:
            chunk = data[:self._max_text - self._text_len]
            self.text_chunks.append(chunk)
            self._text_len += len(chunk)

    def get_text(self):
        return ' '.join(self.text_chunks)

    def error(self, message):
        """Override to prevent exception on malformed HTML."""
        pass


def create_ssl_context(verify=True):
    """Create SSL context with optional verification."""
    ctx = ssl.create_default_context()
    if not verify:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


def validate_url(url):
    """Validate and normalize URL."""
    if not url or not isinstance(url, str):
        return None, "URL is required"

    url = url.strip()[:2000]  # Limit URL length

    # Remove dangerous characters
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
        blocked = ['localhost', '127.0.0.1', '0.0.0.0', '::1', '[::1]']
        if hostname in blocked or hostname.startswith('192.168.') or hostname.startswith('10.') or hostname.startswith('172.'):
            return None, "Local/private URLs not allowed"

        return url, None
    except Exception:
        return None, "Invalid URL format"


def fetch_url(url, timeout=FETCH_TIMEOUT):
    """Fetch URL with proper timeout and error handling."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'identity',  # Avoid compression issues
        'Connection': 'close',
    }

    errors = []

    # Try HTTPS first with verification
    for verify_ssl in [True, False]:
        for protocol in ['https://', 'http://']:
            try:
                test_url = url
                if url.startswith('https://') and protocol == 'http://':
                    test_url = url.replace('https://', 'http://')
                elif url.startswith('http://') and protocol == 'https://':
                    test_url = url.replace('http://', 'https://')
                elif not url.startswith('http'):
                    test_url = protocol + url

                ctx = create_ssl_context(verify=verify_ssl)
                req = urllib.request.Request(test_url, headers=headers)

                with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                    # Check content type
                    content_type = resp.headers.get('Content-Type', '')
                    if not any(t in content_type.lower() for t in ['text/html', 'text/plain', 'application/xhtml']):
                        if 'image' in content_type or 'pdf' in content_type:
                            raise ValueError("Not an HTML page")

                    # Read with size limit
                    html = resp.read(MAX_RESPONSE_SIZE).decode('utf-8', errors='ignore')
                    return html, resp.geturl()

            except urllib.error.HTTPError as e:
                errors.append(f"HTTP {e.code}")
                if e.code in [403, 401]:
                    raise ValueError(f"Access denied (HTTP {e.code})")
            except urllib.error.URLError as e:
                errors.append(str(e.reason)[:50])
            except ssl.SSLError as e:
                errors.append(f"SSL: {str(e)[:30]}")
            except TimeoutError:
                raise
            except Exception as e:
                errors.append(str(e)[:50])

        # Only try without SSL verification if HTTPS failed
        if verify_ssl and 'https' in url:
            continue
        break

    raise ValueError(f"Failed to fetch: {'; '.join(set(errors)[:3])}")


# Safe regex patterns - no catastrophic backtracking

# Simple email pattern - avoids nested quantifiers
EMAIL_PATTERN = re.compile(
    r'[a-zA-Z0-9._%+-]{1,64}@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z]{2,})+',
    re.IGNORECASE
)

MAILTO_PATTERN = re.compile(
    r'mailto:([a-zA-Z0-9._%+-]{1,64}@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
    re.IGNORECASE
)

# Phone patterns - more restrictive
PHONE_PATTERNS = [
    # International with + (e.g., +1-555-123-4567)
    re.compile(r'\+[1-9]\d{0,2}[-.\s]?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}'),
    # US/Canada format (e.g., (555) 123-4567)
    re.compile(r'\(?\d{3}\)[-.\s]?\d{3}[-.\s]?\d{4}(?!\d)'),
    # With explicit tel: prefix
    re.compile(r'tel:[\+]?([0-9\s\-\.\(\)]{10,20})'),
]

# WhatsApp patterns
WHATSAPP_PATTERNS = [
    re.compile(r'wa\.me/(\d{10,15})', re.IGNORECASE),
    re.compile(r'api\.whatsapp\.com/send\?phone=(\d{10,15})', re.IGNORECASE),
    re.compile(r'web\.whatsapp\.com/send\?phone=(\d{10,15})', re.IGNORECASE),
]

# Social media patterns - specific and safe
SOCIAL_PATTERNS = {
    'facebook': re.compile(r'(?:facebook\.com|fb\.com|fb\.me)/(?!sharer|share|dialog|plugins|tr)([a-zA-Z0-9._-]{2,50})/?(?:\?|$|#)', re.IGNORECASE),
    'twitter': re.compile(r'(?:twitter\.com|x\.com)/(?!share|intent|search|hashtag|i/)([a-zA-Z0-9_]{1,15})/?(?:\?|$|#)', re.IGNORECASE),
    'linkedin': re.compile(r'linkedin\.com/(?:in|company)/([a-zA-Z0-9_-]{2,100})/?(?:\?|$|#)', re.IGNORECASE),
    'instagram': re.compile(r'instagram\.com/(?!p/|explore/|accounts/|reel/)([a-zA-Z0-9._]{2,30})/?(?:\?|$|#)', re.IGNORECASE),
    'youtube': re.compile(r'youtube\.com/(?:c/|channel/|user/|@)([a-zA-Z0-9_-]{2,50})/?(?:\?|$|#)', re.IGNORECASE),
    'tiktok': re.compile(r'tiktok\.com/@([a-zA-Z0-9._]{2,24})/?(?:\?|$|#)', re.IGNORECASE),
    'github': re.compile(r'github\.com/(?!features|pricing|enterprise|login|join)([a-zA-Z0-9_-]{1,39})/?(?:\?|$|#)', re.IGNORECASE),
    'telegram': re.compile(r't\.me/(?!share|joinchat)([a-zA-Z0-9_]{5,32})/?(?:\?|$|#)', re.IGNORECASE),
}

# Skip these email patterns (false positives)
EMAIL_SKIP_PATTERNS = [
    r'\.(?:png|jpg|jpeg|gif|svg|webp|ico|css|js|woff|ttf|eot)$',
    r'^(?:no-?reply|noreply|donotreply|mailer-daemon|postmaster|admin|root|webmaster)@',
    r'@(?:example\.com|test\.com|localhost|sentry\.io|wixpress\.com|w3\.org)$',
    r'@[0-9]+x?\.',  # Image dimensions like @2x.png
    r'^[0-9]+@',  # Starts with only numbers
    r'%[0-9a-fA-F]{2}',  # URL-encoded
]

# Skip these social usernames
SOCIAL_SKIP = {
    'share', 'sharer', 'intent', 'login', 'signup', 'register', 'home',
    'about', 'contact', 'help', 'support', 'terms', 'privacy', 'settings',
    'notifications', 'messages', 'search', 'explore', 'trending', 'hashtag',
    'api', 'static', 'assets', 'images', 'js', 'css', 'fonts', 'status',
}


def is_valid_email(email):
    """Check if email is likely a real email address."""
    if not email or len(email) > 100 or len(email) < 6:
        return False

    for pattern in EMAIL_SKIP_PATTERNS:
        if re.search(pattern, email, re.IGNORECASE):
            return False

    parts = email.split('@')
    if len(parts) != 2:
        return False

    local, domain = parts
    if not local or not domain or '.' not in domain:
        return False

    tld = domain.split('.')[-1]
    if len(tld) < 2 or len(tld) > 10 or not tld.isalpha():
        return False

    return True


def extract_all(html, url=""):
    """Extract all contact info from HTML content."""
    result = {
        'emails': [],
        'phones': [],
        'whatsapp': [],
        'social_links': {}
    }

    if not html:
        return result

    # Limit input size to prevent regex performance issues
    text = html[:MAX_INPUT_LENGTH]

    # Extract emails
    seen_emails = set()
    for match in EMAIL_PATTERN.finditer(text):
        email = match.group(0).lower().strip('.')
        if is_valid_email(email) and email not in seen_emails:
            seen_emails.add(email)
            result['emails'].append(email)

    for match in MAILTO_PATTERN.finditer(text):
        email = match.group(1).lower().strip('.')
        if is_valid_email(email) and email not in seen_emails:
            seen_emails.add(email)
            result['emails'].append(email)

    # Limit emails
    result['emails'] = result['emails'][:15]

    # Extract phones
    seen_digits = set()
    for pattern in PHONE_PATTERNS:
        for match in pattern.finditer(text):
            phone = match.group(0) if not match.groups() else match.group(1)
            digits = re.sub(r'\D', '', phone)
            if 10 <= len(digits) <= 15 and digits not in seen_digits:
                # Skip if looks like a date or version number
                if re.search(r'20[0-2]\d[-/]', match.group(0)):
                    continue
                seen_digits.add(digits)
                result['phones'].append({
                    'original': phone.strip(),
                    'digits': digits,
                    'formatted': phone.strip()
                })

    result['phones'] = result['phones'][:10]

    # Extract WhatsApp
    seen_wa = set()
    for pattern in WHATSAPP_PATTERNS:
        for match in pattern.finditer(text):
            num = match.group(1)
            if num and num not in seen_wa and len(num) >= 10:
                seen_wa.add(num)
                result['whatsapp'].append({
                    'number': num,
                    'link': f'https://wa.me/{num}'
                })

    result['whatsapp'] = result['whatsapp'][:5]

    # Extract social links
    for platform, pattern in SOCIAL_PATTERNS.items():
        result['social_links'][platform] = []
        seen = set()
        for match in pattern.finditer(text):
            username = match.group(1).lower().rstrip('/')
            if username not in SOCIAL_SKIP and username not in seen and len(username) >= 2:
                seen.add(username)
                base_urls = {
                    'facebook': 'https://facebook.com/',
                    'twitter': 'https://twitter.com/',
                    'linkedin': 'https://linkedin.com/in/',
                    'instagram': 'https://instagram.com/',
                    'youtube': 'https://youtube.com/@',
                    'tiktok': 'https://tiktok.com/@',
                    'github': 'https://github.com/',
                    'telegram': 'https://t.me/',
                }
                result['social_links'][platform].append({
                    'username': username,
                    'url': base_urls.get(platform, '') + username,
                    'platform': platform
                })

        if not result['social_links'][platform]:
            del result['social_links'][platform]

    return result


def crawl(start_url, max_pages=MAX_PAGES):
    """Crawl website and extract contacts."""
    start_time = time.time()

    # Validate URL
    normalized_url, error = validate_url(start_url)
    if error:
        return {
            'success': False,
            'error': error,
            'source_url': start_url,
            'emails': [],
            'phones': [],
            'whatsapp': [],
            'social_links': {}
        }

    base_domain = urlparse(normalized_url).netloc
    visited = set()
    to_visit = [normalized_url]
    all_data = {
        'emails': [],
        'phones': [],
        'whatsapp': [],
        'social_links': {}
    }
    pages_scraped = 0

    while to_visit and pages_scraped < max_pages:
        # Check total timeout
        elapsed = time.time() - start_time
        if elapsed > TOTAL_TIMEOUT:
            break

        url = to_visit.pop(0)
        if url in visited:
            continue
        visited.add(url)

        try:
            # Per-request timeout
            remaining = max(2, int(TOTAL_TIMEOUT - elapsed))
            html, final_url = fetch_url(url, timeout=min(FETCH_TIMEOUT, remaining))
            pages_scraped += 1

            # Parse and extract
            parser = LinkExtractor()
            try:
                parser.feed(html)
            except Exception:
                pass  # Continue even if parsing fails

            text = parser.get_text()
            data = extract_all(html + ' ' + text, url)

            # Merge results
            for email in data['emails']:
                if email not in all_data['emails']:
                    all_data['emails'].append(email)

            for phone in data['phones']:
                if phone['digits'] not in [p['digits'] for p in all_data['phones']]:
                    all_data['phones'].append(phone)

            for wa in data['whatsapp']:
                if wa['number'] not in [w['number'] for w in all_data['whatsapp']]:
                    all_data['whatsapp'].append(wa)

            for platform, links in data['social_links'].items():
                if platform not in all_data['social_links']:
                    all_data['social_links'][platform] = []
                for link in links:
                    if link['username'] not in [l['username'] for l in all_data['social_links'][platform]]:
                        all_data['social_links'][platform].append(link)

            # Find contact/about pages to crawl next
            if pages_scraped < max_pages:
                for link in parser.links[:30]:
                    try:
                        # Skip external links, anchors, javascript
                        if link.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                            continue

                        full_url = urljoin(final_url, link)
                        parsed = urlparse(full_url)

                        # Must be same domain
                        if parsed.netloc != base_domain:
                            continue

                        # Prioritize contact/about pages
                        path = parsed.path.lower()
                        if any(keyword in path for keyword in ['contact', 'about', 'team', 'support']):
                            if full_url not in visited:
                                to_visit.insert(0, full_url)
                                break
                    except Exception:
                        continue

        except TimeoutError:
            break
        except ValueError as e:
            # Log but continue to next URL
            continue
        except Exception:
            continue

    return {
        'success': True,
        'api_version': 'v3-fixed',
        'source_url': normalized_url,
        'pages_scraped': pages_scraped,
        'time_taken': round(time.time() - start_time, 2),
        'emails': all_data['emails'][:15],
        'phones': all_data['phones'][:10],
        'whatsapp': all_data['whatsapp'][:5],
        'social_links': all_data['social_links']
    }


class handler(BaseHTTPRequestHandler):
    """Vercel serverless function handler."""

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass

    def send_cors_headers(self):
        """Send CORS headers."""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Accept')
        self.send_header('Access-Control-Max-Age', '86400')

    def send_json(self, code, data):
        """Send JSON response."""
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self):
        """Handle GET request - return API info."""
        self.send_json(200, {
            'status': 'ok',
            'message': 'POST {"url": "example.com"} to extract contacts',
            'version': 'v3-fixed',
            'limits': {
                'max_urls': MAX_URLS,
                'max_pages_per_url': MAX_PAGES,
                'timeout_seconds': TOTAL_TIMEOUT
            }
        })

    def do_POST(self):
        """Handle POST request - extract contacts."""
        try:
            # Read and parse request body
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 10000:  # 10KB max request body
                self.send_json(400, {'success': False, 'error': 'Request too large'})
                return

            body = self.rfile.read(content_length).decode('utf-8')

            try:
                data = json.loads(body) if body else {}
            except json.JSONDecodeError:
                self.send_json(400, {'success': False, 'error': 'Invalid JSON'})
                return

            # Get URLs from request
            urls = data.get('urls', [])
            if not urls and data.get('url'):
                urls = [data.get('url')]

            if not urls:
                self.send_json(400, {'success': False, 'error': 'URL required. Send {"url": "example.com"}'})
                return

            # Validate and limit URLs
            urls = [str(u).strip() for u in urls[:MAX_URLS] if u and str(u).strip()]

            if not urls:
                self.send_json(400, {'success': False, 'error': 'No valid URLs provided'})
                return

            max_pages = min(int(data.get('max_pages', 2)), MAX_PAGES)

            # Process URLs
            results = []
            for url in urls:
                try:
                    with timeout_context(TOTAL_TIMEOUT):
                        result = crawl(url, max_pages)
                        results.append(result)
                except TimeoutError:
                    results.append({
                        'success': False,
                        'source_url': url,
                        'error': 'Request timed out',
                        'emails': [],
                        'phones': [],
                        'whatsapp': [],
                        'social_links': {}
                    })
                except Exception as e:
                    results.append({
                        'success': False,
                        'source_url': url,
                        'error': f'Extraction failed: {str(e)[:100]}',
                        'emails': [],
                        'phones': [],
                        'whatsapp': [],
                        'social_links': {}
                    })

            # Return response
            if len(results) == 1:
                self.send_json(200, results[0])
            else:
                self.send_json(200, {
                    'success': True,
                    'results': results,
                    'total_urls': len(results)
                })

        except Exception as e:
            self.send_json(500, {
                'success': False,
                'error': f'Server error: {str(e)[:100]}'
            })
