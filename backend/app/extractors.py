"""
Contact Information Extractors
Regex patterns and extraction logic for emails, phones, social links, and names.
"""

import re
from typing import List, Dict, Set
import phonenumbers
from phonenumbers import PhoneNumberFormat, NumberParseException


class EmailExtractor:
    """Extract email addresses from text content."""

    # Comprehensive email regex pattern
    EMAIL_PATTERN = re.compile(
        r'''(?:[a-zA-Z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-zA-Z0-9!#$%&'*+/=?^_`{|}~-]+)*'''
        r'''|"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]'''
        r'''|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*")'''
        r'''@(?:(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?\.)+[a-zA-Z0-9]'''
        r'''(?:[a-zA-Z0-9-]*[a-zA-Z0-9])?'''
        r'''|\[(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'''
        r'''(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?|[a-zA-Z0-9-]*[a-zA-Z0-9]:'''
        r'''(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]'''
        r'''|\\[\x01-\x09\x0b\x0c\x0e-\x7f])+)\])''',
        re.VERBOSE | re.IGNORECASE
    )

    # Simpler pattern for obfuscated emails
    OBFUSCATED_PATTERNS = [
        re.compile(r'([a-zA-Z0-9._%+-]+)\s*[\[\(]?\s*(?:at|AT|@)\s*[\]\)]?\s*([a-zA-Z0-9.-]+)\s*[\[\(]?\s*(?:dot|DOT|\.)\s*[\]\)]?\s*([a-zA-Z]{2,})', re.IGNORECASE),
        re.compile(r'([a-zA-Z0-9._%+-]+)\s*\[at\]\s*([a-zA-Z0-9.-]+)\s*\[dot\]\s*([a-zA-Z]{2,})', re.IGNORECASE),
    ]

    # Common invalid patterns to filter
    INVALID_PATTERNS = [
        r'.*\.(png|jpg|jpeg|gif|svg|css|js|ico|woff|woff2|ttf|eot)$',
        r'^(noreply|no-reply|donotreply|mailer-daemon|postmaster)@',
        r'.*@(example\.com|test\.com|localhost|127\.0\.0\.1)$',
        r'^[0-9]+@',  # Starts with numbers only
    ]

    @classmethod
    def extract(cls, text: str, html: str = "") -> Set[str]:
        """Extract all valid email addresses from text and HTML."""
        emails = set()

        # Direct pattern matching
        for match in cls.EMAIL_PATTERN.finditer(text):
            email = match.group(0).lower().strip()
            if cls._is_valid_email(email):
                emails.add(email)

        # Check for mailto: links in HTML
        mailto_pattern = re.compile(r'mailto:([^"\'<>\s?]+)', re.IGNORECASE)
        for match in mailto_pattern.finditer(html):
            email = match.group(1).lower().strip()
            if cls._is_valid_email(email):
                emails.add(email)

        # Check for obfuscated emails
        for pattern in cls.OBFUSCATED_PATTERNS:
            for match in pattern.finditer(text):
                email = f"{match.group(1)}@{match.group(2)}.{match.group(3)}".lower()
                if cls._is_valid_email(email):
                    emails.add(email)

        return emails

    @classmethod
    def _is_valid_email(cls, email: str) -> bool:
        """Validate email address."""
        if not email or len(email) > 254:
            return False

        # Check against invalid patterns
        for pattern in cls.INVALID_PATTERNS:
            if re.match(pattern, email, re.IGNORECASE):
                return False

        # Must have valid TLD
        parts = email.split('@')
        if len(parts) != 2:
            return False

        domain = parts[1]
        if '.' not in domain:
            return False

        tld = domain.split('.')[-1]
        if len(tld) < 2 or not tld.isalpha():
            return False

        return True


class PhoneExtractor:
    """Extract phone numbers from text content."""

    # Multiple phone patterns for different formats
    PHONE_PATTERNS = [
        # International format with +
        re.compile(r'\+\d{1,4}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}'),
        # US/Canada format
        re.compile(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'),
        # General international
        re.compile(r'\d{2,4}[-.\s]?\d{2,4}[-.\s]?\d{2,4}[-.\s]?\d{2,4}'),
        # With country code in parentheses
        re.compile(r'\(\+\d{1,4}\)\s?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}'),
    ]

    # Common separators to normalize
    SEPARATORS = re.compile(r'[\s\-\.\(\)]+')

    @classmethod
    def extract(cls, text: str, default_region: str = "US") -> List[Dict]:
        """Extract and validate phone numbers."""
        phones = set()
        seen_numbers = set()

        # Find all potential phone numbers
        for pattern in cls.PHONE_PATTERNS:
            for match in pattern.finditer(text):
                raw_number = match.group(0)

                # Try to parse with phonenumbers library
                try:
                    parsed = phonenumbers.parse(raw_number, default_region)
                    if phonenumbers.is_valid_number(parsed):
                        formatted = phonenumbers.format_number(parsed, PhoneNumberFormat.E164)
                        international = phonenumbers.format_number(parsed, PhoneNumberFormat.INTERNATIONAL)

                        if formatted not in seen_numbers:
                            seen_numbers.add(formatted)
                            phones.add((
                                formatted,
                                international,
                                raw_number.strip()
                            ))
                except NumberParseException:
                    # If parsing fails, still include if it looks like a phone
                    cleaned = cls.SEPARATORS.sub('', raw_number)
                    if 7 <= len(cleaned) <= 15 and cleaned.replace('+', '').isdigit():
                        if cleaned not in seen_numbers:
                            seen_numbers.add(cleaned)
                            phones.add((cleaned, raw_number.strip(), raw_number.strip()))

        return [
            {"e164": p[0], "formatted": p[1], "original": p[2]}
            for p in phones
        ]


class WhatsAppExtractor:
    """Extract WhatsApp contact information."""

    WHATSAPP_PATTERNS = [
        # wa.me links
        re.compile(r'(?:https?://)?(?:www\.)?wa\.me/(\d+)', re.IGNORECASE),
        # api.whatsapp.com links
        re.compile(r'(?:https?://)?api\.whatsapp\.com/send\?phone=(\d+)', re.IGNORECASE),
        # web.whatsapp.com links
        re.compile(r'(?:https?://)?web\.whatsapp\.com/send\?phone=(\d+)', re.IGNORECASE),
        # WhatsApp click-to-chat
        re.compile(r'whatsapp://send\?phone=(\d+)', re.IGNORECASE),
    ]

    @classmethod
    def extract(cls, text: str, html: str = "") -> List[Dict]:
        """Extract WhatsApp numbers from content."""
        whatsapp_numbers = set()
        combined = f"{text} {html}"

        for pattern in cls.WHATSAPP_PATTERNS:
            for match in pattern.finditer(combined):
                number = match.group(1)
                if len(number) >= 10:  # Valid phone length
                    whatsapp_numbers.add(number)

        # Also look for WhatsApp mentioned near phone numbers
        whatsapp_context = re.compile(
            r'(?:whatsapp|wa|wsp)[\s:]*[\+]?(\d{10,15})',
            re.IGNORECASE
        )
        for match in whatsapp_context.finditer(combined):
            number = match.group(1)
            if len(number) >= 10:
                whatsapp_numbers.add(number)

        return [
            {
                "number": num,
                "link": f"https://wa.me/{num}"
            }
            for num in whatsapp_numbers
        ]


class SocialLinkExtractor:
    """Extract social media profile links."""

    SOCIAL_PLATFORMS = {
        'facebook': {
            'patterns': [
                re.compile(r'(?:https?://)?(?:www\.)?(?:facebook|fb)\.com/(?!sharer|share|dialog)([a-zA-Z0-9._-]+)/?', re.IGNORECASE),
                re.compile(r'(?:https?://)?(?:www\.)?fb\.me/([a-zA-Z0-9._-]+)/?', re.IGNORECASE),
            ],
            'base_url': 'https://facebook.com/'
        },
        'twitter': {
            'patterns': [
                re.compile(r'(?:https?://)?(?:www\.)?(?:twitter|x)\.com/(?!share|intent)([a-zA-Z0-9_]+)/?', re.IGNORECASE),
            ],
            'base_url': 'https://twitter.com/'
        },
        'linkedin': {
            'patterns': [
                re.compile(r'(?:https?://)?(?:www\.)?linkedin\.com/(?:in|company)/([a-zA-Z0-9_-]+)/?', re.IGNORECASE),
            ],
            'base_url': 'https://linkedin.com/in/'
        },
        'instagram': {
            'patterns': [
                re.compile(r'(?:https?://)?(?:www\.)?instagram\.com/(?!p/|explore|accounts)([a-zA-Z0-9._]+)/?', re.IGNORECASE),
            ],
            'base_url': 'https://instagram.com/'
        },
        'youtube': {
            'patterns': [
                re.compile(r'(?:https?://)?(?:www\.)?youtube\.com/(?:c/|channel/|user/|@)([a-zA-Z0-9_-]+)/?', re.IGNORECASE),
            ],
            'base_url': 'https://youtube.com/'
        },
        'tiktok': {
            'patterns': [
                re.compile(r'(?:https?://)?(?:www\.)?tiktok\.com/@([a-zA-Z0-9._]+)/?', re.IGNORECASE),
            ],
            'base_url': 'https://tiktok.com/@'
        },
        'pinterest': {
            'patterns': [
                re.compile(r'(?:https?://)?(?:www\.)?pinterest\.com/([a-zA-Z0-9_]+)/?', re.IGNORECASE),
            ],
            'base_url': 'https://pinterest.com/'
        },
        'github': {
            'patterns': [
                re.compile(r'(?:https?://)?(?:www\.)?github\.com/([a-zA-Z0-9_-]+)/?', re.IGNORECASE),
            ],
            'base_url': 'https://github.com/'
        },
        'telegram': {
            'patterns': [
                re.compile(r'(?:https?://)?(?:www\.)?t\.me/([a-zA-Z0-9_]+)/?', re.IGNORECASE),
                re.compile(r'(?:https?://)?(?:www\.)?telegram\.me/([a-zA-Z0-9_]+)/?', re.IGNORECASE),
            ],
            'base_url': 'https://t.me/'
        },
    }

    # Invalid usernames to filter
    INVALID_USERNAMES = {
        'share', 'sharer', 'intent', 'dialog', 'login', 'signup', 'register',
        'home', 'about', 'contact', 'help', 'support', 'terms', 'privacy',
        'settings', 'notifications', 'messages', 'search', 'explore', 'trending',
        'hashtag', 'i', 'js', 'css', 'images', 'static', 'assets', 'api',
    }

    @classmethod
    def extract(cls, text: str, html: str = "") -> Dict[str, List[Dict]]:
        """Extract social media links from content."""
        social_links = {platform: [] for platform in cls.SOCIAL_PLATFORMS}
        combined = f"{text} {html}"
        seen = {platform: set() for platform in cls.SOCIAL_PLATFORMS}

        for platform, config in cls.SOCIAL_PLATFORMS.items():
            for pattern in config['patterns']:
                for match in pattern.finditer(combined):
                    username = match.group(1).lower().rstrip('/')

                    # Filter invalid usernames
                    if username in cls.INVALID_USERNAMES:
                        continue
                    if len(username) < 2:
                        continue

                    if username not in seen[platform]:
                        seen[platform].add(username)
                        full_url = match.group(0)
                        if not full_url.startswith('http'):
                            full_url = 'https://' + full_url.lstrip('/')

                        social_links[platform].append({
                            'username': username,
                            'url': full_url,
                            'platform': platform
                        })

        # Remove empty platforms
        return {k: v for k, v in social_links.items() if v}


class NameExtractor:
    """Extract potential contact names from content."""

    # Patterns for names near contact info
    NAME_PATTERNS = [
        # "Contact: John Doe" or "Contact John Doe"
        re.compile(r'(?:contact|manager|owner|founder|ceo|director|author|by)[\s:]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})', re.IGNORECASE),
        # "John Doe, CEO"
        re.compile(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})[\s,]+(?:ceo|founder|owner|manager|director|president)', re.IGNORECASE),
        # Names in meta tags
        re.compile(r'(?:author|contact)["\s:]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})', re.IGNORECASE),
    ]

    # Common words that aren't names
    EXCLUDED_WORDS = {
        'contact', 'about', 'home', 'page', 'site', 'website', 'email', 'phone',
        'address', 'company', 'business', 'service', 'services', 'product',
        'products', 'privacy', 'policy', 'terms', 'conditions', 'copyright',
        'rights', 'reserved', 'loading', 'please', 'wait', 'click', 'here',
        'read', 'more', 'learn', 'view', 'all', 'see', 'get', 'started',
        'subscribe', 'newsletter', 'follow', 'share', 'social', 'media',
    }

    @classmethod
    def extract(cls, text: str, html: str = "") -> List[str]:
        """Extract potential names from content."""
        names = set()
        combined = f"{text}"

        for pattern in cls.NAME_PATTERNS:
            for match in pattern.finditer(combined):
                name = match.group(1).strip()
                # Validate name
                if cls._is_valid_name(name):
                    names.add(name)

        # Look for names in common HTML patterns
        name_html_patterns = [
            re.compile(r'<meta[^>]+name=["\']author["\'][^>]+content=["\']([^"\']+)["\']', re.IGNORECASE),
            re.compile(r'class=["\'][^"\']*(?:author|name|contact-name)[^"\']*["\'][^>]*>([^<]+)<', re.IGNORECASE),
        ]

        for pattern in name_html_patterns:
            for match in pattern.finditer(html):
                name = match.group(1).strip()
                if cls._is_valid_name(name):
                    names.add(name)

        return list(names)[:10]  # Limit to top 10 names

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
            if not word.isalpha():
                return False

        # At least one word should start with uppercase
        if not any(w[0].isupper() for w in name.split()):
            return False

        return True


class AddressExtractor:
    """Extract physical addresses from content."""

    # US Address pattern
    US_ADDRESS = re.compile(
        r'\d{1,5}\s+[\w\s]{1,30}(?:street|st|avenue|ave|road|rd|highway|hwy|square|sq|trail|trl|drive|dr|court|ct|parkway|pkwy|circle|cir|boulevard|blvd)\.?(?:\s+(?:apt|apartment|suite|ste|unit|#)\s*\.?\s*\d+)?[\s,]+[\w\s]+,\s*[A-Z]{2}\s+\d{5}(?:-\d{4})?',
        re.IGNORECASE
    )

    # Generic address with postal code
    GENERIC_ADDRESS = re.compile(
        r'(?:\d{1,5}\s+)?[\w\s]{2,40}[,\s]+[\w\s]{2,30}[,\s]+[\w\s]{2,30}[,\s]+(?:\d{4,10}|[A-Z]{1,2}\d{1,2}\s?\d[A-Z]{2})',
        re.IGNORECASE
    )

    @classmethod
    def extract(cls, text: str) -> List[str]:
        """Extract addresses from content."""
        addresses = set()

        # US addresses
        for match in cls.US_ADDRESS.finditer(text):
            addr = ' '.join(match.group(0).split())
            if len(addr) > 15:
                addresses.add(addr)

        # Generic addresses
        for match in cls.GENERIC_ADDRESS.finditer(text):
            addr = ' '.join(match.group(0).split())
            if len(addr) > 20 and len(addr) < 200:
                addresses.add(addr)

        return list(addresses)[:5]
