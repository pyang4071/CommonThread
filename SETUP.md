# CommonThread — Setup & Deployment

---

## Local Development

### Prerequisites
- Python 3.12+
- Node.js 18+
- PostgreSQL with `pgvector` extension (or a Supabase project)

### Backend

```bash
cd backend
cp .env.example .env          # fill in Supabase credentials + DATABASE_URL
uv run alembic upgrade head   # run all migrations
uv run fastapi dev app/main.py
# API at http://localhost:8000 | auto-docs at http://localhost:8000/docs
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local    # fill in VITE_SUPABASE_URL + VITE_SUPABASE_ANON_KEY
npm run dev
# Dev server at http://localhost:5173 (proxies /api → localhost:8000)
```

### Useful Commands

```bash
# Backend
uv run ruff check .                                        # lint
uv run ruff format .                                       # format
uv run alembic revision --autogenerate -m "description"   # new migration
uv run alembic upgrade head                                # apply migrations
uv run alembic downgrade -1                                # roll back one
# A migration that creates a table must ENABLE ROW LEVEL SECURITY on it and list it
# in RLS_TABLES (tests/test_rls_coverage.py enforces this).

# Repo root — secret scanning (gitleaks) on every commit; run once per clone
pre-commit install

# Frontend
npm run build    # production build — also runs tsc, surfaces type errors
npm run lint     # ESLint
npm run preview  # preview production build locally
```

---

## Environment Variables

### Backend (`backend/.env`)

```env
SUPABASE_URL=https://<ref>.supabase.co
SUPABASE_ANON_KEY=<anon-key>
SUPABASE_SERVICE_ROLE_KEY=<service-role-key>
DATABASE_URL=postgresql+asyncpg://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres
SECRET_KEY=change-me-in-production
ENVIRONMENT=development
```

> `SYNC_DATABASE_URL` is computed from `DATABASE_URL` by `config.py` (replaces `asyncpg` with `psycopg` for Alembic). Do not set it manually.

### Frontend (`frontend/.env.local`)

```env
VITE_SUPABASE_URL=https://<ref>.supabase.co
VITE_SUPABASE_ANON_KEY=<anon-key>
```

---

## Docker

```bash
cp backend/.env.example backend/.env   # fill in credentials
docker compose up --build
# Frontend:  http://localhost
# Backend:   http://localhost:8000
# API docs:  http://localhost:8000/docs
```

FastEmbed models (~570 MB) are downloaded on first startup and cached in a named Docker volume (`fastembed_cache`). Subsequent starts are instant.

---

## Deployment (Railway + Vercel)

**Backend → Railway**: set root directory to `backend/`, Dockerfile path to `backend/Dockerfile`, and add env vars from `backend/.env.example`. Railway builds on every push to `main`. Mount `/root/.cache/huggingface` as a persistent volume to avoid re-downloading models on redeploy.

**Frontend → Vercel**: set root directory to `frontend/`, add `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, and `VITE_API_BASE_URL`. Add a `vercel.json` to proxy `/api/*` to your Railway service URL and rewrite all other paths to `/index.html`.

---

## End-to-End Tests

```bash
cd e2e
npm install
cp .env.example .env   # fill in TEST_EMAIL, ADMIN_EMAIL, SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY
                       # use dedicated test accounts — global-teardown signs their sessions out after each run

npm test                              # all 135 tests
npx playwright test --project=public  # 16 public tests — no credentials needed
npx playwright test --ui              # interactive UI mode
```

See [docs/features.md — End-to-End Testing](docs/features.md#end-to-end-testing) for full test coverage details.
