# CONTACT EXTRACTOR - COMPLETE OUTPUT FOR SPREADSHEET

## VERIFIED & PRODUCTION-READY
All issues fixed - Copy sections directly into your Google Sheets/Excel.

---

## SECTION 1: PROJECT FILES (31 Total)

| File | Path | Purpose |
|------|------|---------|
| main.py | backend/app/main.py | FastAPI server with all endpoints |
| extractors.py | backend/app/extractors.py | Regex patterns for emails, phones, social |
| scraper.py | backend/app/scraper.py | Web scraping engine (static + dynamic) |
| __init__.py | backend/app/__init__.py | Python package init |
| requirements.txt | backend/requirements.txt | Python dependencies (full) |
| requirements-minimal.txt | backend/requirements-minimal.txt | Python dependencies (no Playwright) |
| Dockerfile | backend/Dockerfile | Backend container |
| railway.json | backend/railway.json | Railway deployment config |
| App.jsx | frontend/src/App.jsx | React UI with copy/export features |
| main.jsx | frontend/src/main.jsx | React entry point |
| index.css | frontend/src/index.css | Tailwind CSS styles |
| index.html | frontend/index.html | HTML template |
| package.json | frontend/package.json | Node.js dependencies |
| vite.config.js | frontend/vite.config.js | Vite build config |
| tailwind.config.js | frontend/tailwind.config.js | Tailwind config |
| postcss.config.js | frontend/postcss.config.js | PostCSS config |
| Dockerfile | frontend/Dockerfile | Frontend container |
| nginx.conf | frontend/nginx.conf | Nginx for frontend |
| vercel.json | frontend/vercel.json | Vercel deployment |
| .env | frontend/.env | Environment variables |
| .env.example | frontend/.env.example | Example env file |
| favicon.svg | frontend/public/favicon.svg | App icon |
| docker-compose.yml | root | Full stack Docker |
| nginx.conf | root | Main nginx config |
| render.yaml | root | Render deployment |
| .gitignore | root | Git ignore rules |
| README.md | root | Documentation |
| start-backend.sh | root | Linux/Mac start script |
| start-backend.bat | root | Windows backend start |
| start-frontend.bat | root | Windows frontend start |
| COPY_TO_SHEET.md | root | This file |

---

## SECTION 2: API ENDPOINTS

| Method | Endpoint | Description | Request Body |
|--------|----------|-------------|--------------|
| GET | / | Health check | - |
| GET | /health | Health check | - |
| GET | /docs | Swagger docs | - |
| POST | /extract | Sync extraction | {"url": "https://site.com", "max_pages": 10, "use_dynamic": false, "timeout": 30} |
| POST | /extract/async | Async job | {"url": "https://site.com"} |
| GET | /extract/status/{job_id} | Check job status | - |
| POST | /batch-extract | Multiple URLs (max 10) | ["url1", "url2"] |
| POST | /extract/export | CSV-ready format | {"url": "https://site.com"} |

---

## SECTION 3: EXTRACTION PATTERNS

### Email Patterns
| Pattern Type | Example | Detection Method |
|--------------|---------|------------------|
| Standard | user@domain.com | RFC 5322 regex |
| Obfuscated | user [at] domain [dot] com | Custom patterns |
| Mailto Link | mailto:user@domain.com | HTML parsing |

### Phone Patterns
| Format | Example | Library |
|--------|---------|---------|
| International | +1 555 123 4567 | phonenumbers |
| US/Canada | (555) 123-4567 | phonenumbers |
| European | +44 20 7946 0958 | phonenumbers |
| Generic | Any 7-15 digit | Custom regex |

### Social Media Platforms
| Platform | Pattern | Example |
|----------|---------|---------|
| Facebook | facebook.com/username | facebook.com/company |
| Twitter/X | twitter.com/username | twitter.com/handle |
| LinkedIn | linkedin.com/in/username | linkedin.com/in/john-doe |
| Instagram | instagram.com/username | instagram.com/brand |
| YouTube | youtube.com/@channel | youtube.com/@creator |
| TikTok | tiktok.com/@username | tiktok.com/@influencer |
| GitHub | github.com/username | github.com/developer |
| Telegram | t.me/username | t.me/channel |
| Pinterest | pinterest.com/username | pinterest.com/brand |

### WhatsApp Patterns
| Type | Example URL |
|------|-------------|
| wa.me | https://wa.me/15551234567 |
| API | https://api.whatsapp.com/send?phone=15551234567 |
| Web | https://web.whatsapp.com/send?phone=15551234567 |

---

## SECTION 4: RESPONSE FORMAT

### Single Extraction Response (JSON)
```
{
  "success": true,
  "source_url": "https://example.com",
  "pages_scraped": 5,
  "emails": ["contact@example.com", "info@example.com"],
  "phones": [
    {"e164": "+15551234567", "formatted": "+1 555 123 4567", "original": "(555) 123-4567"}
  ],
  "whatsapp": [
    {"number": "15551234567", "link": "https://wa.me/15551234567"}
  ],
  "social_links": {
    "facebook": [{"username": "company", "url": "https://facebook.com/company", "platform": "facebook"}],
    "twitter": [{"username": "handle", "url": "https://twitter.com/handle", "platform": "twitter"}]
  },
  "names": ["John Doe"],
  "addresses": ["123 Main St, New York, NY 10001"],
  "extracted_at": "2024-01-15T10:30:00.000Z"
}
```

---

## SECTION 5: QUICK START COMMANDS

### Windows (Recommended)
```
# Terminal 1 - Backend
cd contact-extractor
start-backend.bat

# Terminal 2 - Frontend
cd contact-extractor
start-frontend.bat
```

### Docker (Production)
```
cd contact-extractor
docker-compose up --build -d
# Open http://localhost:3000
```

### Manual Setup
```
# Backend (Terminal 1)
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
uvicorn app.main:app --reload --port 8000

# Frontend (Terminal 2)
cd frontend
npm install
npm run dev
```

---

## SECTION 6: ENVIRONMENT VARIABLES

| Variable | File | Dev Value | Prod Value |
|----------|------|-----------|------------|
| VITE_API_URL | frontend/.env | http://localhost:8000 | https://your-api.railway.app |

---

## SECTION 7: DEPLOYMENT

### Vercel (Frontend)
1. Push to GitHub
2. Connect to Vercel
3. Set root: `frontend`
4. Set VITE_API_URL to your backend URL
5. Deploy

### Railway (Backend)
1. Push to GitHub
2. Connect to Railway
3. Set root: `backend`
4. Deploy (uses railway.json)

### Render (Full Stack)
1. Push to GitHub
2. Connect to Render
3. Uses render.yaml blueprint
4. Deploys both services

---

## SECTION 8: CSV EXPORT FORMAT

| Type | Value | Formatted | Platform | Link | Source |
|------|-------|-----------|----------|------|--------|
| email | user@example.com | user@example.com | | mailto:user@example.com | https://example.com |
| phone | +15551234567 | +1 555 123 4567 | | tel:+15551234567 | https://example.com |
| whatsapp | 15551234567 | 15551234567 | whatsapp | https://wa.me/15551234567 | https://example.com |
| social | username | @username | twitter | https://twitter.com/username | https://example.com |
| name | John Doe | John Doe | | | https://example.com |

---

## SECTION 9: TECH STACK

| Layer | Technology | Version |
|-------|------------|---------|
| Backend Framework | FastAPI | 0.109.0 |
| Web Scraping | BeautifulSoup4 | 4.12.3 |
| Dynamic Scraping | Playwright | 1.41.0 |
| HTTP Client | httpx | 0.26.0 |
| Phone Parsing | phonenumbers | 8.13.27 |
| Validation | pydantic | 2.5.3 |
| Frontend Framework | React | 18.2.0 |
| Build Tool | Vite | 5.0.12 |
| CSS Framework | TailwindCSS | 3.4.1 |
| Icons | Lucide React | 0.312.0 |
| HTTP Client | Axios | 1.6.5 |
| Containerization | Docker | Latest |

---

## SECTION 10: FEATURES CHECKLIST

| Feature | Status | Notes |
|---------|--------|-------|
| Email extraction | YES | Standard + obfuscated + mailto |
| Phone extraction | YES | International + validation |
| WhatsApp links | YES | wa.me, api, web formats |
| Facebook | YES | Profile URLs |
| Twitter/X | YES | Profile URLs |
| LinkedIn | YES | Personal + Company |
| Instagram | YES | Profile URLs |
| YouTube | YES | Channels |
| TikTok | YES | Profile URLs |
| GitHub | YES | Profile URLs |
| Telegram | YES | Profile URLs |
| Pinterest | YES | Profile URLs |
| Name extraction | YES | From contact pages |
| Address extraction | YES | US + international |
| Copy to clipboard | YES | Individual + bulk + fallback |
| CSV export | YES | One-click download |
| Async processing | YES | Background jobs |
| Batch processing | YES | Up to 10 URLs |
| Dynamic JS sites | YES | Playwright fallback |
| Docker deployment | YES | docker-compose |
| Vercel deployment | YES | vercel.json included |
| Railway deployment | YES | railway.json included |
| Render deployment | YES | render.yaml included |
| Health checks | YES | /health endpoint |
| Swagger docs | YES | /docs endpoint |
| CORS enabled | YES | Configurable origins |
| SSL handling | YES | Ignores cert errors |
| No AI/paid APIs | YES | 100% self-hosted |

---

## SECTION 11: cURL TEST COMMANDS

### Basic Extraction
```
curl -X POST http://localhost:8000/extract -H "Content-Type: application/json" -d "{\"url\": \"example.com\", \"max_pages\": 5}"
```

### With Dynamic Scraping
```
curl -X POST http://localhost:8000/extract -H "Content-Type: application/json" -d "{\"url\": \"example.com\", \"use_dynamic\": true}"
```

### Batch Extraction
```
curl -X POST http://localhost:8000/batch-extract -H "Content-Type: application/json" -d "[\"site1.com\", \"site2.com\"]"
```

### Health Check
```
curl http://localhost:8000/health
```

---

## SECTION 12: TROUBLESHOOTING

| Issue | Solution |
|-------|----------|
| CORS error | Check allow_origins in main.py |
| SSL errors | Already handled with verify=False |
| Playwright fails | Run: playwright install chromium |
| Port in use | Change port in uvicorn command |
| No contacts found | Enable use_dynamic for JS sites |
| Timeout | Increase timeout value (max 120s) |

---

END OF OUTPUT - All sections verified and production-ready.
