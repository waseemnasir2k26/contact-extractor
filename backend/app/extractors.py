"""
Contact Information Extractors
Safe regex patterns and extraction logic for emails, phones, social links, and names.

Fixed issues:
- No catastrophic backtracking in regex patterns
- Input length limits before regex matching
- Better filtering of false positives
- Handling of mobile URLs and URL parameters
"""

import re
from typing import List, Dict, Set, Optional

# Try to import phonenumbers, but make it optional
try:
    import phonenumbers
    from phonenumbers import PhoneNumberFormat, NumberParseException
    HAS_PHONENUMBERS = True
except ImportError:
    HAS_PHONENUMBERS = False

# Constants
MAX_TEXT_LENGTH = 500000  # 500KB max text to process
MAX_RESULTS_PER_TYPE = 50


def truncate_text(text: str, max_length: int = MAX_TEXT_LENGTH) -> str:
    """Safely truncate text to prevent regex performance issues."""
    if not text:
        return ""
    return text[:max_length]


class EmailExtractor:
    """Extract email addresses from text content."""

    # Simple, safe email pattern - no nested quantifiers
    # Matches: user@domain.tld, user.name@sub.domain.com
    EMAIL_PATTERN = re.compile(
        r'[a-zA-Z0-9._%+-]{1,64}@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?'
        r'(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}',
        re.IGNORECASE
    )

    # Mailto pattern for HTML
    MAILTO_PATTERN = re.compile(
        r'mailto:([a-zA-Z0-9._%+-]{1,64}@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
        re.IGNORECASE
    )

    # Obfuscated email patterns (user [at] domain [dot] com)
    OBFUSCATED_PATTERN = re.compile(
        r'([a-zA-Z0-9._%+-]{1,64})\s*[\[\(]?\s*(?:at|AT|@)\s*[\]\)]?\s*'
        r'([a-zA-Z0-9.-]{1,100})\s*[\[\(]?\s*(?:dot|DOT|\.)\s*[\]\)]?\s*'
        r'([a-zA-Z]{2,10})',
        re.IGNORECASE
    )

    # Patterns to skip (false positives)
    SKIP_PATTERNS = [
        re.compile(r'\.(?:png|jpg|jpeg|gif|svg|webp|ico|bmp|tiff?)$', re.I),
        re.compile(r'\.(?:css|js|json|xml|woff2?|ttf|eot|otf)$', re.I),
        re.compile(r'^(?:no-?reply|noreply|donotreply|mailer-daemon)@', re.I),
        re.compile(r'^(?:postmaster|admin|root|webmaster|hostmaster)@', re.I),
        re.compile(r'@(?:example\.com|test\.com|localhost|127\.0\.0\.1)$', re.I),
        re.compile(r'@(?:sentry\.io|wixpress\.com|w3\.org|schema\.org)$', re.I),
        re.compile(r'@\d+x?\.', re.I),  # @2x.png style image names
        re.compile(r'^\d+@', re.I),  # Starts with only numbers
        re.compile(r'%[0-9a-fA-F]{2}'),  # URL encoded
        re.compile(r'^[a-f0-9]{32}@', re.I),  # MD5-like strings
    ]

    @classmethod
    def extract(cls, text: str, html: str = "") -> Set[str]:
        """Extract all valid email addresses from text and HTML."""
        text = truncate_text(text)
        html = truncate_text(html)
        emails = set()

        # Direct pattern matching
        for match in cls.EMAIL_PATTERN.finditer(text):
            email = match.group(0).lower().strip('.')
            if cls._is_valid_email(email):
                emails.add(email)
                if len(emails) >= MAX_RESULTS_PER_TYPE:
                    break

        # Check for mailto: links in HTML
        if len(emails) < MAX_RESULTS_PER_TYPE:
            for match in cls.MAILTO_PATTERN.finditer(html):
                email = match.group(1).lower().strip('.')
                if cls._is_valid_email(email):
                    emails.add(email)
                    if len(emails) >= MAX_RESULTS_PER_TYPE:
                        break

        # Check for obfuscated emails
        if len(emails) < MAX_RESULTS_PER_TYPE:
            for match in cls.OBFUSCATED_PATTERN.finditer(text):
                try:
                    email = f"{match.group(1)}@{match.group(2)}.{match.group(3)}".lower()
                    if cls._is_valid_email(email):
                        emails.add(email)
                        if len(emails) >= MAX_RESULTS_PER_TYPE:
                            break
                except Exception:
                    continue

        return emails

    @classmethod
    def _is_valid_email(cls, email: str) -> bool:
        """Validate email address."""
        if not email or len(email) > 254 or len(email) < 6:
            return False

        # Check against skip patterns
        for pattern in cls.SKIP_PATTERNS:
            if pattern.search(email):
                return False

        # Must have valid structure
        parts = email.split('@')
        if len(parts) != 2:
            return False

        local, domain = parts
        if not local or not domain or len(local) > 64:
            return False

        if '.' not in domain:
            return False

        tld = domain.split('.')[-1]
        if len(tld) < 2 or len(tld) > 10 or not tld.isalpha():
            return False

        return True


class PhoneExtractor:
    """Extract phone numbers from text content."""

    # Safe phone patterns - no nested quantifiers
    PHONE_PATTERNS = [
        # International with + (e.g., +1-555-123-4567, +44 20 7123 4567)
        re.compile(r'\+[1-9]\d{0,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{2,4}[-.\s]?\d{2,4}[-.\s]?\d{0,4}'),
        # US/Canada format (e.g., (555) 123-4567, 555-123-4567)
        re.compile(r'\(?\d{3}\)[-.\s]?\d{3}[-.\s]?\d{4}(?!\d)'),
        # Tel: links
        re.compile(r'tel:\+?([0-9\s\-\.\(\)]{10,20})'),
        # Href phone links
        re.compile(r'href=["\']tel:([^"\']+)["\']'),
    ]

    # Patterns that look like phones but aren't
    SKIP_PATTERNS = [
        re.compile(r'20[0-2]\d[-/]\d{1,2}[-/]\d{1,2}'),  # Dates: 2024-01-15
        re.compile(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'),  # IP addresses
        re.compile(r'\d+\.\d+\.\d+'),  # Version numbers: 1.2.3
        re.compile(r'[a-zA-Z]\d{10,}'),  # IDs with letters
    ]

    @classmethod
    def extract(cls, text: str, default_region: str = "US") -> List[Dict]:
        """Extract and validate phone numbers."""
        text = truncate_text(text)
        phones = []
        seen_digits = set()

        for pattern in cls.PHONE_PATTERNS:
            for match in pattern.finditer(text):
                try:
                    raw = match.group(1) if match.lastindex and match.lastindex >= 1 else match.group(0)
                    raw = raw.strip()

                    # Skip if matches a skip pattern
                    skip = False
                    for skip_pattern in cls.SKIP_PATTERNS:
                        if skip_pattern.search(raw):
                            skip = True
                            break
                    if skip:
                        continue

                    # Extract digits only
                    digits = re.sub(r'\D', '', raw)

                    # Validate length
                    if not (10 <= len(digits) <= 15):
                        continue

                    # Skip if already seen
                    if digits in seen_digits:
                        continue

                    seen_digits.add(digits)

                    # Try to parse with phonenumbers library if available
                    if HAS_PHONENUMBERS:
                        try:
                            parsed = phonenumbers.parse(raw, default_region)
                            if phonenumbers.is_valid_number(parsed):
                                e164 = phonenumbers.format_number(parsed, PhoneNumberFormat.E164)
                                formatted = phonenumbers.format_number(parsed, PhoneNumberFormat.INTERNATIONAL)
                                phones.append({
                                    "e164": e164,
                                    "formatted": formatted,
                                    "original": raw
                                })
                            else:
                                # Invalid according to phonenumbers, but include anyway with raw format
                                phones.append({
                                    "e164": digits,
                                    "formatted": raw,
                                    "original": raw
                                })
                        except Exception:
                            phones.append({
                                "e164": digits,
                                "formatted": raw,
                                "original": raw
                            })
                    else:
                        phones.append({
                            "e164": digits,
                            "formatted": raw,
                            "original": raw
                        })

                    if len(phones) >= MAX_RESULTS_PER_TYPE:
                        break

                except Exception:
                    continue

            if len(phones) >= MAX_RESULTS_PER_TYPE:
                break

        return phones


class WhatsAppExtractor:
    """Extract WhatsApp contact information."""

    WHATSAPP_PATTERNS = [
        # wa.me links (with optional params)
        re.compile(r'(?:https?://)?(?:www\.)?wa\.me/(\d{10,15})(?:\?[^\s"\'<>]*)?', re.IGNORECASE),
        # api.whatsapp.com links
        re.compile(r'(?:https?://)?api\.whatsapp\.com/send\?(?:[^&\s]*&)*phone=(\d{10,15})', re.IGNORECASE),
        # web.whatsapp.com links
        re.compile(r'(?:https?://)?web\.whatsapp\.com/send\?(?:[^&\s]*&)*phone=(\d{10,15})', re.IGNORECASE),
        # WhatsApp URI scheme
        re.compile(r'whatsapp://send\?phone=(\d{10,15})', re.IGNORECASE),
        # Business WhatsApp
        re.compile(r'(?:https?://)?(?:www\.)?wa\.link/(\w+)', re.IGNORECASE),
    ]

    # WhatsApp mentioned near number
    CONTEXT_PATTERN = re.compile(
        r'(?:whatsapp|wa|wsp|watsapp)[\s:]*\+?(\d{10,15})',
        re.IGNORECASE
    )

    @classmethod
    def extract(cls, text: str, html: str = "") -> List[Dict]:
        """Extract WhatsApp numbers from content."""
        text = truncate_text(text)
        html = truncate_text(html)
        combined = f"{text} {html}"

        whatsapp_numbers = set()

        for pattern in cls.WHATSAPP_PATTERNS:
            for match in pattern.finditer(combined):
                number = match.group(1)
                if number and len(number) >= 10:
                    whatsapp_numbers.add(number)
                    if len(whatsapp_numbers) >= MAX_RESULTS_PER_TYPE:
                        break

            if len(whatsapp_numbers) >= MAX_RESULTS_PER_TYPE:
                break

        # Context pattern
        if len(whatsapp_numbers) < MAX_RESULTS_PER_TYPE:
            for match in cls.CONTEXT_PATTERN.finditer(combined):
                number = match.group(1)
                if number and len(number) >= 10:
                    whatsapp_numbers.add(number)
                    if len(whatsapp_numbers) >= MAX_RESULTS_PER_TYPE:
                        break

        return [
            {
                "number": num,
                "link": f"https://wa.me/{num}"
            }
            for num in whatsapp_numbers
        ]


class SocialLinkExtractor:
    """Extract social media profile links."""

    # Platform configurations with safe patterns
    SOCIAL_PLATFORMS = {
        'facebook': {
            'patterns': [
                # Standard and mobile URLs
                re.compile(r'(?:https?://)?(?:www\.|m\.|mobile\.)?(?:facebook|fb)\.com/'
                          r'(?!sharer|share|dialog|plugins|tr|login|signup|watch|groups/[^/]+/permalink|events|marketplace|gaming|help)'
                          r'([a-zA-Z0-9._-]{2,50})/?(?:\?|$|#|")', re.IGNORECASE),
                re.compile(r'(?:https?://)?fb\.me/([a-zA-Z0-9._-]{2,50})/?(?:\?|$|#)', re.IGNORECASE),
            ],
            'base_url': 'https://facebook.com/'
        },
        'twitter': {
            'patterns': [
                # Twitter and X.com, including mobile
                re.compile(r'(?:https?://)?(?:www\.|mobile\.)?(?:twitter|x)\.com/'
                          r'(?!share|intent|search|hashtag|i/|home|explore|notifications|messages|settings|login|signup)'
                          r'([a-zA-Z0-9_]{1,15})/?(?:\?|$|#|")', re.IGNORECASE),
            ],
            'base_url': 'https://twitter.com/'
        },
        'linkedin': {
            'patterns': [
                re.compile(r'(?:https?://)?(?:www\.|[a-z]{2}\.)?linkedin\.com/'
                          r'(?:in|company)/([a-zA-Z0-9_-]{2,100})/?(?:\?|$|#|")', re.IGNORECASE),
            ],
            'base_url': 'https://linkedin.com/in/'
        },
        'instagram': {
            'patterns': [
                # Standard and mobile
                re.compile(r'(?:https?://)?(?:www\.|m\.)?instagram\.com/'
                          r'(?!p/|reel/|explore/|accounts/|direct/|stories/|tv/|about/|legal/)'
                          r'([a-zA-Z0-9._]{2,30})/?(?:\?|$|#|")', re.IGNORECASE),
            ],
            'base_url': 'https://instagram.com/'
        },
        'youtube': {
            'patterns': [
                re.compile(r'(?:https?://)?(?:www\.|m\.)?youtube\.com/'
                          r'(?:c/|channel/|user/|@)([a-zA-Z0-9_-]{2,50})/?(?:\?|$|#|")', re.IGNORECASE),
                re.compile(r'(?:https?://)?youtu\.be/([a-zA-Z0-9_-]{11})(?:\?|$|#)', re.IGNORECASE),
            ],
            'base_url': 'https://youtube.com/@'
        },
        'tiktok': {
            'patterns': [
                re.compile(r'(?:https?://)?(?:www\.|m\.)?tiktok\.com/@([a-zA-Z0-9._]{2,24})/?(?:\?|$|#|")', re.IGNORECASE),
                re.compile(r'(?:https?://)?vm\.tiktok\.com/([a-zA-Z0-9]+)/?', re.IGNORECASE),
            ],
            'base_url': 'https://tiktok.com/@'
        },
        'pinterest': {
            'patterns': [
                re.compile(r'(?:https?://)?(?:www\.|[a-z]{2}\.)?pinterest\.(?:com|co\.uk|de|fr|es|it)/'
                          r'(?!pin/)([a-zA-Z0-9_-]{2,30})/?(?:\?|$|#|")', re.IGNORECASE),
            ],
            'base_url': 'https://pinterest.com/'
        },
        'github': {
            'patterns': [
                re.compile(r'(?:https?://)?(?:www\.)?github\.com/'
                          r'(?!features|pricing|enterprise|login|join|explore|topics|trending|collections|sponsors|marketplace|apps|settings|notifications)'
                          r'([a-zA-Z0-9_-]{1,39})/?(?:\?|$|#|")', re.IGNORECASE),
            ],
            'base_url': 'https://github.com/'
        },
        'telegram': {
            'patterns': [
                re.compile(r'(?:https?://)?(?:www\.)?t\.me/'
                          r'(?!share|joinchat|addstickers|setlanguage)'
                          r'([a-zA-Z0-9_]{5,32})/?(?:\?|$|#|")', re.IGNORECASE),
                re.compile(r'(?:https?://)?telegram\.me/([a-zA-Z0-9_]{5,32})/?(?:\?|$|#)', re.IGNORECASE),
            ],
            'base_url': 'https://t.me/'
        },
    }

    # Invalid usernames to always filter
    INVALID_USERNAMES = {
        'share', 'sharer', 'intent', 'dialog', 'login', 'signup', 'register',
        'home', 'about', 'contact', 'help', 'support', 'terms', 'privacy',
        'settings', 'notifications', 'messages', 'search', 'explore', 'trending',
        'hashtag', 'i', 'js', 'css', 'images', 'static', 'assets', 'api',
        'status', 'jobs', 'careers', 'press', 'blog', 'legal', 'policy',
        'watch', 'feed', 'null', 'undefined', 'true', 'false', 'none',
    }

    @classmethod
    def extract(cls, text: str, html: str = "") -> Dict[str, List[Dict]]:
        """Extract social media links from content."""
        text = truncate_text(text)
        html = truncate_text(html)
        combined = f"{text} {html}"

        social_links = {}

        for platform, config in cls.SOCIAL_PLATFORMS.items():
            seen = set()
            links = []

            for pattern in config['patterns']:
                for match in pattern.finditer(combined):
                    try:
                        username = match.group(1)
                        if not username:
                            continue

                        # Normalize username
                        username = username.lower().rstrip('/').strip()

                        # Skip invalid usernames
                        if username in cls.INVALID_USERNAMES:
                            continue
                        if len(username) < 2:
                            continue
                        if username.isdigit():  # Pure numeric usernames are usually not valid
                            continue

                        if username not in seen:
                            seen.add(username)

                            # Build URL
                            full_match = match.group(0)
                            if full_match.startswith('http'):
                                url = full_match.rstrip('"\'').rstrip('/')
                            else:
                                url = config['base_url'] + username

                            links.append({
                                'username': username,
                                'url': url,
                                'platform': platform
                            })

                            if len(links) >= MAX_RESULTS_PER_TYPE:
                                break

                    except Exception:
                        continue

                if len(links) >= MAX_RESULTS_PER_TYPE:
                    break

            if links:
                social_links[platform] = links

        return social_links


class NameExtractor:
    """Extract potential contact names from content."""

    # Patterns for names near contact info - safe patterns
    NAME_PATTERNS = [
        # "Contact: John Doe" or "Contact John Doe"
        re.compile(r'(?:contact|manager|owner|founder|ceo|director|author|by)[\s:]+([A-Z][a-z]{1,20}(?:\s+[A-Z][a-z]{1,20}){1,2})', re.IGNORECASE),
        # "John Doe, CEO"
        re.compile(r'([A-Z][a-z]{1,20}(?:\s+[A-Z][a-z]{1,20}){1,2})[\s,]+(?:ceo|founder|owner|manager|director|president|cto|cfo)', re.IGNORECASE),
    ]

    # HTML patterns for author/name meta
    HTML_PATTERNS = [
        re.compile(r'<meta[^>]+name=["\']author["\'][^>]+content=["\']([^"\']{3,50})["\']', re.IGNORECASE),
        re.compile(r'<meta[^>]+content=["\']([^"\']{3,50})["\'][^>]+name=["\']author["\']', re.IGNORECASE),
        re.compile(r'class=["\'][^"\']*(?:author-name|contact-name|person-name)[^"\']*["\'][^>]*>([^<]{3,50})<', re.IGNORECASE),
    ]

    # Words that aren't names
    EXCLUDED_WORDS = {
        'contact', 'about', 'home', 'page', 'site', 'website', 'email', 'phone',
        'address', 'company', 'business', 'service', 'services', 'product',
        'products', 'privacy', 'policy', 'terms', 'conditions', 'copyright',
        'rights', 'reserved', 'loading', 'please', 'wait', 'click', 'here',
        'read', 'more', 'learn', 'view', 'all', 'see', 'get', 'started',
        'subscribe', 'newsletter', 'follow', 'share', 'social', 'media',
        'admin', 'administrator', 'null', 'undefined', 'true', 'false',
    }

    @classmethod
    def extract(cls, text: str, html: str = "") -> List[str]:
        """Extract potential names from content."""
        text = truncate_text(text, 100000)  # Smaller limit for names
        html = truncate_text(html, 100000)
        names = set()

        # Text patterns
        for pattern in cls.NAME_PATTERNS:
            for match in pattern.finditer(text):
                name = match.group(1).strip()
                if cls._is_valid_name(name):
                    names.add(name)
                    if len(names) >= 10:
                        break

        # HTML patterns
        if len(names) < 10:
            for pattern in cls.HTML_PATTERNS:
                for match in pattern.finditer(html):
                    name = match.group(1).strip()
                    if cls._is_valid_name(name):
                        names.add(name)
                        if len(names) >= 10:
                            break

        return list(names)[:10]

    @classmethod
    def _is_valid_name(cls, name: str) -> bool:
        """Check if extracted text is likely a valid name."""
        if not name or len(name) < 3 or len(name) > 50:
            return False

        words = name.lower().split()
        if len(words) < 1 or len(words) > 4:
            return False

        # Check each word
        for word in words:
            if word in cls.EXCLUDED_WORDS:
                return False
            if not word.replace('-', '').replace("'", '').isalpha():
                return False

        # At least one word should have proper capitalization
        original_words = name.split()
        if not any(w[0].isupper() for w in original_words if w):
            return False

        return True


class AddressExtractor:
    """Extract physical addresses from content."""

    # US Address pattern - safe, no backtracking
    US_ADDRESS = re.compile(
        r'\d{1,5}\s+[A-Za-z0-9\s]{1,30}'
        r'(?:street|st|avenue|ave|road|rd|highway|hwy|drive|dr|court|ct|boulevard|blvd|lane|ln|way|place|pl|circle|cir)\.?'
        r'(?:\s+(?:apt|apartment|suite|ste|unit|#)\s*\.?\s*[A-Za-z0-9-]+)?'
        r'[\s,]+[A-Za-z\s]{2,30},?\s*[A-Z]{2}\s+\d{5}(?:-\d{4})?',
        re.IGNORECASE
    )

    # UK postcode pattern
    UK_ADDRESS = re.compile(
        r'[A-Za-z0-9\s,]{10,50}\s+[A-Z]{1,2}\d{1,2}\s?\d[A-Z]{2}',
        re.IGNORECASE
    )

    @classmethod
    def extract(cls, text: str) -> List[str]:
        """Extract addresses from content."""
        text = truncate_text(text, 100000)
        addresses = set()

        # US addresses
        for match in cls.US_ADDRESS.finditer(text):
            addr = ' '.join(match.group(0).split())
            if 15 < len(addr) < 200:
                addresses.add(addr)
                if len(addresses) >= 5:
                    break

        # UK addresses
        if len(addresses) < 5:
            for match in cls.UK_ADDRESS.finditer(text):
                addr = ' '.join(match.group(0).split())
                if 15 < len(addr) < 200:
                    addresses.add(addr)
                    if len(addresses) >= 5:
                        break

        return list(addresses)[:5]
