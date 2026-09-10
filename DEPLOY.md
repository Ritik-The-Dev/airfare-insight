# FareLens Deployment Guide

Both services deploy to Vercel as **separate projects** from the same repo.

| Service | Vercel Project | Root Directory |
|---------|---------------|----------------|
| Frontend (React/TanStack) | `farelens` | `/` (repo root) |
| Backend (FastAPI) | `farelens-api` | `backend/` |

---

## Step 1 — Deploy the Backend

1. Go to https://vercel.com → **Add New Project**
2. Import your GitHub repo
3. Set **Root Directory**: `backend`
4. Framework: **Other**
5. Build/output settings: leave blank (Vercel detects `api/index.py` automatically)
6. Add **Environment Variables**:

```
DATABASE_URL        = postgresql://postgres.xufxqbhwnhpnkxhdadxd:PASSWORD@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres
SUPABASE_URL        = https://xufxqbhwnhpnkxhdadxd.supabase.co
SUPABASE_KEY        = your-service-role-key
IGNAV_API_KEY       = ignav_JaygezSb88PrlIBq2sAU9ftpL1YzyqE5
CORS_ORIGINS        = ["https://your-frontend.vercel.app","http://localhost:5173"]
LOG_LEVEL           = INFO
CACHE_TTL           = 60
SCRAPER_TIMEOUT     = 30
DEMO_MODE           = false
PLAYWRIGHT_HEADLESS = true
```

7. Deploy → note the URL, e.g. `https://farelens-api.vercel.app`
8. Verify: `https://farelens-api.vercel.app/api/health` → `{"status":"ok"}`

---

## Step 2 — Deploy the Frontend

1. Go to https://vercel.com → **Add New Project**
2. Import the **same** GitHub repo
3. **Root Directory**: leave as `/` (repo root)
4. **Framework**: Other
5. **Build command**: `npm run build`
6. **Output directory**: `.vercel/output`
7. Add **Environment Variables**:

```
VITE_API_BASE_URL = https://farelens-api.vercel.app
```

8. Deploy

---

## Step 3 — Update CORS on the backend

Once you know the frontend URL, go back to the backend Vercel project → Settings → Environment Variables → update:

```
CORS_ORIGINS = ["https://your-actual-frontend.vercel.app","http://localhost:5173"]
```

Redeploy the backend.

---

## Step 4 — Verify end-to-end

1. Open `https://your-frontend.vercel.app` → CPI dashboard loads
2. Click "Search Live Fares" → search works, flights appear
3. Check `https://farelens-api.vercel.app/api/fare-observations/summary` → returns data
4. Check `https://farelens-api.vercel.app/api/docs` → Swagger UI

---

## Important notes

- `backend/.env` is gitignored — set ALL secrets in Vercel dashboard, never in code
- Vercel serverless functions have a **10 second timeout** on free plan. The Ignav API call typically takes 2–3s so this is fine.
- Playwright scrapers are **not used** in the current build (Ignav API is used instead), so no Chrome binary issues.
- Vercel Python serverless uses the `requirements-prod.txt` equivalent — `playwright` is excluded since it's not needed.
