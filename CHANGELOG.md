# Changelog

## [2.0.0] - 2024-02-09

### Major Fixes - Serverless API (`api/extract.py`)

#### Timeout & Performance
- **FIXED**: Added hard timeout enforcement using SIGALRM signal (9s total)
- **FIXED**: Removed global `socket.setdefaulttimeout()` pollution
- **FIXED**: Reduced per-request timeout to 6 seconds
- **FIXED**: Limited response size to 200KB per page
- **FIXED**: Limited max pages to 3 and max URLs to 5

#### Security & Validation
- **ADDED**: URL validation function with:
  - Protocol normalization (adds https:// if missing)
  - Control character removal
  - Local/private IP blocking (localhost, 192.168.*, 10.*, 172.*)
  - URL length limiting (2000 chars max)
- **FIXED**: SSL verification enabled by default, falls back to disabled only if needed
- **ADDED**: Request body size limit (10KB max)

#### Regex Patterns (Backtracking Prevention)
- **FIXED**: Replaced complex RFC 5322 email pattern with simple, safe pattern
- **FIXED**: Phone patterns now exclude dates (2024-01-15) and version numbers
- **FIXED**: Added negative lookahead to prevent false matches
- **ADDED**: Input text truncation before regex processing (500KB limit)

#### Email Filtering
- **ADDED**: Filters for:
  - Image files (.png, .jpg, .svg, etc.)
  - CSS/JS files
  - System emails (noreply, postmaster, etc.)
  - Image dimensions (@2x.png style)
  - URL-encoded strings
  - Numbers-only local parts

#### Social Media
- **ADDED**: Twitter/X.com dual support
- **FIXED**: Patterns exclude share/login/intent URLs
- **ADDED**: More skip usernames (api, static, assets, etc.)

### Major Fixes - Frontend (`frontend/src/App.jsx`)

#### State Management
- **FIXED**: Added `mountedRef` to track component lifecycle
- **FIXED**: All state updates check mount state before executing
- **FIXED**: Proper cleanup on unmount (timer + abort controller)
- **REMOVED**: Unused `debugInfo` state

#### Request Handling
- **ADDED**: Retry logic with exponential backoff (1 retry)
- **ADDED**: Proper AbortController integration with axios
- **FIXED**: Timer properly cleaned up on all exit paths
- **ADDED**: Request timeout of 25 seconds

#### Error Handling
- **ADDED**: `parseError()` function for consistent error categorization:
  - `cancelled` - User cancelled request
  - `timeout` - Request timed out
  - `network` - Network connectivity issue
  - `not_found` - API endpoint not found
  - `rate_limit` - Too many requests
  - `server_error` - Server error
  - `gateway_error` - 502/503/504 errors
- **ADDED**: Specific, helpful error messages for each type
- **ADDED**: Retry indicator in UI

#### URL Validation
- **ADDED**: Client-side URL validation before sending
- **ADDED**: URL normalization (adds https://)
- **IMPROVED**: Better placeholder text for inputs

#### UI Improvements
- **ADDED**: Retry count indicator during requests
- **IMPROVED**: Progress bar calculation
- **IMPROVED**: Result cards with unique keys
- **IMPROVED**: Transition animations

### Major Fixes - Backend (`backend/app/`)

#### Extractors (`extractors.py`)
- **FIXED**: All regex patterns rewritten to prevent catastrophic backtracking
- **ADDED**: `truncate_text()` function with 500KB default limit
- **ADDED**: `MAX_RESULTS_PER_TYPE = 50` limit
- **FIXED**: Made `phonenumbers` library optional with graceful fallback
- **ADDED**: Mobile URL support for all social platforms (m.facebook.com, etc.)
- **ADDED**: Country-specific TLD support (pinterest.co.uk, linkedin.de, etc.)
- **ADDED**: More comprehensive skip patterns for false positives

#### Scraper (`scraper.py`)
- **FIXED**: Proper timeout on all HTTP requests
- **FIXED**: SSL verification with fallback
- **ADDED**: URL validation function
- **ADDED**: Private IP blocking
- **ADDED**: Max redirects limit (5)
- **ADDED**: Response size limit (500KB)
- **ADDED**: Link count limit per page (100)
- **IMPROVED**: Error handling with specific exception types
- **ADDED**: Logging support

#### Main API (`main.py`)
- **ADDED**: Global exception handler
- **ADDED**: `asyncio.wait_for()` timeout on all extraction calls
- **ADDED**: URL validation on all endpoints
- **ADDED**: Private IP blocking
- **FIXED**: Proper async job cleanup
- **ADDED**: Request size limits

### Configuration Changes

#### `vite.config.js`
- **ADDED**: Proxy timeout configuration (60s)
- **ADDED**: Build optimization with manual chunks
- **ADDED**: Dependency pre-bundling

### Files Changed

| File | Type | Changes |
|------|------|---------|
| `api/extract.py` | Rewrite | Timeout, validation, regex, error handling |
| `frontend/src/App.jsx` | Rewrite | State, retries, errors, validation |
| `backend/app/extractors.py` | Rewrite | Safe regex, limits, mobile URLs |
| `backend/app/scraper.py` | Rewrite | Timeout, SSL, validation |
| `backend/app/main.py` | Update | Validation, timeout, error handling |
| `frontend/vite.config.js` | Update | Proxy timeout, build optimization |
| `AUDIT_LOG.md` | New | Comprehensive audit documentation |
| `CHANGELOG.md` | New | This file |

### Breaking Changes

- **API Response**: Now includes `api_version: 'v3-fixed'` field
- **Timeouts**: Reduced from 20s to 9s for serverless, 25s for frontend
- **Limits**: Max 3 pages per URL, max 5 URLs per request

### Migration Notes

1. Update any code that depends on 20+ second timeouts
2. Frontend timeout is now 25s (was effectively unlimited)
3. Results are now capped at stricter limits
4. Some previously matched patterns may no longer match (false positives removed)

### Testing Recommendations

1. Test with various website types:
   - Static HTML sites
   - JavaScript-heavy SPAs
   - Sites with contact pages
   - Sites without contact info
2. Test timeout handling:
   - Slow websites
   - Unresponsive websites
3. Test error scenarios:
   - Invalid URLs
   - Network disconnection
   - Request cancellation
4. Test edge cases:
   - Obfuscated emails
   - International phone numbers
   - Mobile social media URLs
