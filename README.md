# Contact Extractor

A production-ready web application that extracts contact information (emails, phone numbers, WhatsApp, social media links) from any website. **No AI APIs or paid services required** - 100% self-hosted.

## Features

- **Email Extraction**: Detects standard and obfuscated email formats
- **Phone Numbers**: International format detection with validation
- **WhatsApp**: Extracts wa.me links and WhatsApp API URLs
- **Social Media**: Facebook, Twitter, LinkedIn, Instagram, YouTube, TikTok, GitHub, Telegram
- **Contact Names**: Extracts names from contact pages
- **Physical Addresses**: Detects US and international address formats
- **Export Options**: Copy to clipboard or export as CSV

## Tech Stack

- **Frontend**: React 18 + Vite + TailwindCSS
- **Backend**: Python FastAPI + BeautifulSoup + Playwright
- **Deployment**: Docker, Vercel, Railway, Render

## Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone and run
git clone https://github.com/yourusername/contact-extractor.git
cd contact-extractor
docker-compose up --build
```

Open http://localhost:3000

### Option 2: Local Development

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
playwright install chromium
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## API Endpoints

### Extract Contacts (Sync)
```bash
POST /extract
{
  "url": "https://example.com",
  "max_pages": 10,
  "use_dynamic": false,
  "timeout": 30
}
```

### Extract Contacts (Async)
```bash
POST /extract/async
# Returns job_id

GET /extract/status/{job_id}
# Returns status and results
```

### Batch Extract
```bash
POST /batch-extract
["https://site1.com", "https://site2.com"]
```

### Export Format
```bash
POST /extract/export
# Returns spreadsheet-friendly format
```

## Deployment

### Vercel (Frontend) + Railway (Backend)

1. **Backend on Railway:**
   - Push to GitHub
   - Connect to Railway
   - Deploy from `/backend` folder
   - Note your deployment URL

2. **Frontend on Vercel:**
   - Connect to Vercel
   - Set root directory to `/frontend`
   - Add environment variable: `VITE_API_URL=https://your-railway-url.railway.app`
   - Deploy

### Render (Full Stack)

```bash
# Uses render.yaml blueprint
# Push to GitHub and connect to Render
```

## Project Structure

```
contact-extractor/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py          # FastAPI application
│   │   ├── scraper.py       # Web scraping logic
│   │   └── extractors.py    # Regex patterns & extractors
│   ├── requirements.txt
│   ├── Dockerfile
│   └── railway.json
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Main React component
│   │   ├── main.jsx
│   │   └── index.css
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── Dockerfile
│   └── vercel.json
├── docker-compose.yml
├── nginx.conf
├── render.yaml
└── README.md
```

## Configuration

### Backend Settings

| Setting | Default | Description |
|---------|---------|-------------|
| max_pages | 10 | Maximum pages to crawl |
| timeout | 30 | Request timeout in seconds |
| use_dynamic | false | Use Playwright for JS sites |

### CORS

Update `app/main.py` for production:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    ...
)
```

## Scraping Strategy

1. **Static First**: Uses `httpx` + BeautifulSoup for fast static scraping
2. **Dynamic Fallback**: Playwright (headless Chromium) for JavaScript-rendered sites
3. **Smart Crawling**: Prioritizes contact, about, team pages
4. **Rate Limiting**: Respectful crawling with delays

## Regex Patterns

### Emails
- Standard: `user@domain.com`
- Obfuscated: `user [at] domain [dot] com`
- Mailto links

### Phones
- International: `+1 (555) 123-4567`
- US/Canada: `(555) 123-4567`
- European: `+44 20 7946 0958`

### Social Media
- Detects profile URLs for 9+ platforms
- Filters out share/intent links
- Extracts usernames

## License

MIT License - Use freely for personal and commercial projects.

## Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Submit pull request

---

Built with Python and React. No AI APIs required.
