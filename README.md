# Contact Extractor

**Paste a website, get its public emails, phone numbers, WhatsApp links and social profiles as a table or CSV. No login, no AI API keys.**

![License: MIT](https://img.shields.io/badge/License-MIT-green)

Building a lead list by clicking through "Contact" pages is slow. This crawls a few pages of a site and pulls the contact details out.

## What it does

- Finds emails (including common obfuscated forms), international phone numbers, `wa.me` and WhatsApp links.
- Finds profiles on Facebook, Twitter/X, LinkedIn, Instagram, YouTube, TikTok, GitHub, Telegram and Pinterest.
- Exports to the clipboard or CSV.
- FastAPI backend (`backend/`) with `/extract`, `/extract/async`, `/extract/status/{job_id}`, `/batch-extract` and `/extract/export`; React + Vite frontend (`frontend/`). `docker-compose.yml` runs both.

## Quickstart (local)

```bash
git clone https://github.com/waseemnasir2k26/contact-extractor
cd contact-extractor

# terminal 1: backend
cd backend
python -m venv venv && source venv/bin/activate     # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# terminal 2: frontend
cd frontend
npm install
npm run dev
```

Call the API directly:

```bash
curl -X POST http://localhost:8000/extract \
  -H "Content-Type: application/json" \
  -d '{"url": "example.com", "max_pages": 5}'
```

To host it free: deploy `backend/` to Render (Docker runtime) and `frontend/` to Vercel with Root Directory set to `frontend` and `VITE_API_URL` pointing at your backend URL. `COPY_TO_SHEET.md` covers sending results to a spreadsheet.

## For you if

You do outreach research and want a self-hosted extractor you control instead of a paid scraper tool.

## Status and limits

- There is no public hosted instance listed here; you run your own.
- Only public pages are read. Check each site's terms and the privacy laws that apply to the data you collect (GDPR, PECR, CAN-SPAM) before you contact anyone.
- JavaScript-heavy sites may return less. Free Render instances sleep when idle.
- Last reviewed October 2026.

## Built by SkynetLabs

Built by [SkynetLabs](https://skynetjoe.com). Questions: info@skynetjoe.com

Need this wired into your business? SkynetLabs builds voice agents, n8n back offices and sites that convert → https://skynetjoe.com
