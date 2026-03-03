# Deployment Guide: Render.com + Supabase

## Step 1: Set Up Supabase Database

1. Go to [supabase.com](https://supabase.com) and create a new project
2. Wait for the project to initialize (~2 minutes)
3. Go to **SQL Editor** (left sidebar)
4. Copy the contents of `supabase/migrations/000_full_schema.sql` and paste into the editor
5. Click **Run** — this creates all 20 tables, indexes, RLS policies, and seed data
6. Go to **Settings > API** and copy:
   - **Project URL** (e.g., `https://abcdef.supabase.co`)
   - **anon public** key (starts with `eyJ...`)

## Step 2: Deploy to Render.com

### Option A: Blueprint (recommended)

1. Push the repo to GitHub (if not already)
2. Go to [render.com](https://render.com) > **New** > **Blueprint**
3. Connect your GitHub repo
4. Render will detect `render.yaml` and create 2 services:
   - **cfd-api** — FastAPI REST API
   - **cfd-dashboard** — Streamlit Dashboard
5. Set environment variables for both services:
   - `CFD_SUPABASE_URL` = your Supabase Project URL
   - `CFD_SUPABASE_KEY` = your Supabase anon key

### Option B: Manual setup

#### API Service
1. **New** > **Web Service** > connect GitHub repo
2. **Environment**: Docker
3. **Dockerfile Path**: `./Dockerfile`
4. Add env vars:
   - `CFD_SUPABASE_URL` = Supabase URL
   - `CFD_SUPABASE_KEY` = Supabase anon key
   - `CFD_API_KEYS` = `demo-test-key-2024`
   - `CFD_API_CORS_ORIGINS` = `*`
5. **Health Check Path**: `/health`

#### Dashboard Service
1. **New** > **Web Service** > connect same repo
2. **Environment**: Docker
3. **Dockerfile Path**: `./Dockerfile.dashboard`
4. Add env vars:
   - `CFD_SUPABASE_URL` = same Supabase URL
   - `CFD_SUPABASE_KEY` = same Supabase key

## Step 3: Test

### API (Swagger UI)
Open `https://cfd-api-xxxx.onrender.com/api/docs` — interactive API documentation.

Test endpoints:
- `GET /health` — no auth needed
- `POST /api/v1/batch/analyze` — use header `X-API-Key: demo-test-key-2024`

### Dashboard
Open `https://cfd-dashboard-xxxx.onrender.com` — interactive Streamlit UI.

Go to **Author Dossier** page:
1. Enter an author surname (e.g., `Einstein`)
2. Enter a Scopus ID or ORCID
3. Click **Analyze** — runs real-time analysis via OpenAlex (free, no API key needed)

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CFD_SUPABASE_URL` | For DB features | `""` | Supabase project URL |
| `CFD_SUPABASE_KEY` | For DB features | `""` | Supabase anon key |
| `CFD_API_KEYS` | For API auth | `""` | Comma-separated API keys (fallback when DB unavailable) |
| `CFD_API_CORS_ORIGINS` | No | `*` | CORS allowed origins |
| `CFD_SCOPUS_API_KEY` | No | `""` | Scopus API key (optional, falls back to OpenAlex) |
| `CFD_DEFAULT_LANGUAGE` | No | `ua` | Interface language (`ua` or `en`) |

## Architecture

```
Browser
  |
  |--- https://cfd-api.onrender.com/api/docs     (Swagger UI)
  |         |
  |         |--- /health                          (health check)
  |         |--- /api/v1/batch/analyze            (batch analysis)
  |         |--- /api/v1/author/{id}/report       (cached reports)
  |         |--- /api/v1/watchlist                 (monitoring)
  |
  |--- https://cfd-dashboard.onrender.com         (Streamlit)
            |
            |--- Overview                         (watchlist table)
            |--- Author Dossier                   (real-time analysis)
            |--- Snapshot Compare                 (score history)
            |--- Anti-Ranking                     (suspicion leaderboard)
            |
            +--- OpenAlex API (free, no key needed)
            +--- Supabase (PostgreSQL)
```

## Notes

- First deploy takes ~5-10 minutes (Docker build)
- Free Render tier spins down after 15 min of inactivity; first request after idle takes ~30 seconds
- OpenAlex API is free and does not require an API key
- Supabase free tier: 500 MB database, 50K monthly requests
