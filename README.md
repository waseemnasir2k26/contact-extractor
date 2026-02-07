# Contact Extractor

Extract emails, phone numbers, WhatsApp links & social media profiles from any website. **Free to use - No login required - No AI APIs needed**.

## Live Demo

- **Frontend**: [Deployed on Vercel]
- **Backend API**: [Deployed on Render]

## Features

- **Email Extraction**: Standard + obfuscated formats
- **Phone Numbers**: International validation
- **WhatsApp**: wa.me and API links
- **Social Media**: Facebook, Twitter, LinkedIn, Instagram, YouTube, TikTok, GitHub, Telegram, Pinterest
- **Export**: Copy to clipboard or download CSV
- **No Login**: Anyone can use it for free

## Deploy Your Own (Free)

### Step 1: Deploy Backend to Render (Free)

1. Go to [render.com](https://render.com) and sign up (free)
2. Click **New > Web Service**
3. Connect your GitHub repo
4. Configure:
   - **Name**: `contact-extractor-api`
   - **Root Directory**: `backend`
   - **Runtime**: `Docker`
   - **Instance Type**: `Free`
5. Click **Create Web Service**
6. Wait for deployment (~5 mins)
7. Copy your URL (e.g., `https://contact-extractor-api.onrender.com`)

### Step 2: Deploy Frontend to Vercel (Free)

**IMPORTANT: Follow these steps exactly to avoid 404 errors**

1. Go to [vercel.com](https://vercel.com) and sign up (free)
2. Click **Add New > Project**
3. Import your GitHub repo
4. **CRITICAL SETTINGS:**
   - **Root Directory**: Click "Edit" and type `frontend` (REQUIRED!)
   - **Framework Preset**: Select `Vite`
   - **Build Command**: `npm run build` (auto-detected)
   - **Output Directory**: `dist` (auto-detected)
5. Click **Environment Variables** and add:
   - **Name**: `VITE_API_URL`
   - **Value**: Your Render backend URL (e.g., `https://contact-extractor-api.onrender.com`)
6. Click **Deploy**
7. Your app is live!

### Fixing 404 Errors on Vercel

If you see a 404 error after deployment:

1. Go to your Vercel project dashboard
2. Click **Settings** > **General**
3. Scroll to **Root Directory**
4. Change it to `frontend`
5. Click **Save**
6. Go to **Deployments** tab
7. Click the three dots on the latest deployment
8. Click **Redeploy**

## Local Development

```bash
# Clone
git clone https://github.com/waseemnasir2k26/contact-extractor.git
cd contact-extractor

# Backend (Terminal 1)
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (Terminal 2)
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

## API Usage

```bash
# Extract contacts
curl -X POST https://your-api.onrender.com/extract \
  -H "Content-Type: application/json" \
  -d '{"url": "example.com", "max_pages": 5}'
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | React 18, Vite, TailwindCSS |
| Backend | Python, FastAPI, BeautifulSoup |
| Deployment | Vercel (frontend), Render (backend) |

## License

MIT - Free for personal and commercial use.

---

**No AI APIs. No paid services. 100% free.**
