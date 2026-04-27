# CommonThread — Railway + Vercel Deployment Guide

This guide covers the one-time manual setup for deploying the backend on Railway and the frontend on Vercel.

**Prerequisites**: Supabase project with `pgvector` enabled, Railway account, Vercel account, repo pushed to GitHub.

---

## 1. Railway — Backend

### 1a. Create the service

1. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**
2. Select the `CommonThread` repository
3. Set **Root Directory** to `backend/`
4. Railway will auto-detect the `Dockerfile` — confirm it points to `backend/Dockerfile`

### 1b. Set environment variables

In the Railway dashboard → your service → **Variables**, add each of the following:

| Variable | Value |
|---|---|
| `SUPABASE_URL` | `https://<ref>.supabase.co` |
| `SUPABASE_ANON_KEY` | your Supabase anon key |
| `SUPABASE_SERVICE_ROLE_KEY` | your Supabase service role key |
| `DATABASE_URL` | `postgresql+asyncpg://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres` |
| `SECRET_KEY` | output of `openssl rand -hex 32` |
| `ENVIRONMENT` | `production` |
| `CORS_ORIGINS` | `["https://<your-vercel-domain>.vercel.app"]` *(fill in after Vercel step)* |
| `CROWD_PROMOTION_THRESHOLD` | `3` |

> **`DATABASE_URL` note**: Use the **Session pooler** (port 5432), not the Transaction pooler, for SQLAlchemy async connections. Copy it from Supabase → Project Settings → Database → Connection string, and swap the scheme to `postgresql+asyncpg`.

### 1c. Add a persistent volume for FastEmbed models

The BGE embedding models are ~570 MB. Without a persistent volume they re-download on every deploy.

1. Railway dashboard → your service → **Volumes**
2. **Add Volume** → mount path: `/root/.cache/fastembed`
3. Any size ≥ 1 GB is sufficient

### 1d. Note your Railway service URL

Once deployed, Railway assigns a public URL like `https://<service-name>.up.railway.app`. Copy it — you need it in the next two steps.

---

## 2. Update `frontend/vercel.json`

Open `frontend/vercel.json` and replace the placeholder with your Railway URL:

```json
{
  "rewrites": [
    { "source": "/api/:path*", "destination": "https://<service-name>.up.railway.app/api/:path*" },
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

Commit and push this change before deploying on Vercel.

---

## 3. Vercel — Frontend

### 3a. Create the project

1. Go to [vercel.com](https://vercel.com) → **Add New Project** → import the `CommonThread` repository
2. Set **Root Directory** to `frontend/`
3. Framework preset: **Vite** (Vercel usually auto-detects this)

### 3b. Set environment variables

In the Vercel dashboard → your project → **Settings** → **Environment Variables**, add:

| Variable | Value |
|---|---|
| `VITE_SUPABASE_URL` | `https://<ref>.supabase.co` |
| `VITE_SUPABASE_ANON_KEY` | your Supabase anon key |
| `VITE_API_BASE_URL` | `https://<service-name>.up.railway.app` *(your Railway URL, no trailing slash)* |

> These are **build-time** variables baked into the JS bundle by Vite. Changes require a redeploy.

### 3c. Deploy

Click **Deploy**. Vercel builds `frontend/` using `npm run build` and serves `dist/` through its CDN.

Once deployed, copy your Vercel domain (e.g. `https://common-thread.vercel.app`) and go back to Railway to fill in `CORS_ORIGINS`.

---

## 4. Update `CORS_ORIGINS` on Railway

Back in Railway → your service → **Variables**, update:

```
CORS_ORIGINS=["https://<your-project>.vercel.app"]
```

Railway will redeploy automatically. After it restarts, the frontend on Vercel can reach the backend.

---

## 5. Verify the deployment

1. Open your Vercel URL — the home page should load
2. Sign in with a Supabase account — the auth flow should complete
3. Browse to `/books` — the book list should load from the Railway backend
4. Open `https://<service-name>.up.railway.app/health` — should return `{"status":"ok","models":{...}}`
   - Models show `"loading"` on the first cold start while FastEmbed downloads (~2–5 min)
   - They flip to `"ready"` once downloaded; the admin `/embed-all` flow then works normally

---

## Re-deploys

| What changed | What to redeploy |
|---|---|
| Backend Python code | Railway auto-deploys on push to `main` |
| Frontend React code | Vercel auto-deploys on push to `main` |
| New `VITE_*` env var | Trigger a manual Vercel redeploy (env vars are baked at build time) |
| New backend env var | Railway picks it up on next deploy or restart |
| New Alembic migration | Run `uv run alembic upgrade head` from your local machine against the prod DB before deploying the code that needs it |
