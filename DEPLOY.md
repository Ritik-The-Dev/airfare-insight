# FareLens Deployment Guide

Two services, two platforms:

| Service | Platform | URL |
|---------|----------|-----|
| Frontend (React/TanStack) | Vercel | `https://your-app.vercel.app` |
| Backend (FastAPI) | Render | `https://farelens-api.onrender.com` |

---

## 1. Deploy the Backend (Render)

### Why Render, not Vercel?
Vercel Python serverless has a 250MB limit and no persistent processes. FastAPI + asyncpg needs a real server process. Render free tier provides this.

### Steps

1. Go to https://render.com → New → Web Service
2. Connect your GitHub repo
3. Set **Root directory**: `backend`
4. Set **Build command**: `pip install -r requirements-prod.txt`
5. Set **Start command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
6. Set **Runtime**: Python 3.12
7. Add environment variables:

```
DATABASE_URL=postgresql://postgres.xufxqbhwnhpnkxhdadxd:PASSWORD@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres
SUPABASE_URL=https://xufxqbhwnhpnkxhdadxd.supabase.co
SUPABASE_KEY=your-service-role-key
IGNAV_API_KEY=ignav_JaygezSb88PrlIBq2sAU9ftpL1YzyqE5
CORS_ORIGINS=["https://your-app.vercel.app","http://localhost:5173"]
LOG_LEVEL=INFO
CACHE_TTL=60
SCRAPER_TIMEOUT=30
DEMO_MODE=false
```

8. Deploy. Note the URL: `https://farelens-api.onrender.com`

---

## 2. Deploy the Frontend (Vercel)

### Steps

1. Go to https://vercel.com → New Project
2. Import your GitHub repo
3. **Framework preset**: Other (not Next.js)
4. **Build command**: `npm run build`
5. **Output directory**: `.output/public`
6. **Install command**: `npm install`
7. Add environment variable:

```
VITE_API_BASE_URL=https://farelens-api.onrender.com
```

8. Deploy.

### Important: Update CORS on backend

After you know your Vercel URL, go back to Render and update `CORS_ORIGINS`:
```
CORS_ORIGINS=["https://your-actual-app.vercel.app","http://localhost:5173"]
```

---

## 3. Verify deployment

1. Open `https://your-app.vercel.app` → CPI Dashboard loads
2. Check `https://farelens-api.onrender.com/api/health` → `{"status": "ok"}`
3. Check `https://farelens-api.onrender.com/api/docs` → Swagger UI
4. Do a flight search on the frontend → results appear

---

## Notes

- Render free tier sleeps after 15 minutes of inactivity. First request after sleep takes ~30s.
- Playwright scrapers won't work on Render free tier either (no Chrome). The Ignav API approach is used instead.
- `backend/.env` is gitignored — set all secrets via Render's environment variable UI.
