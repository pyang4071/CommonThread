# CommonThread

A book recommendation engine powered by tropes and character archetypes. CommonThread models books at the level of narrative DNA — tropes and archetypes with weighted importance — and uses a three-stream semantic embedding approach (structural genome, prose description, aggregated reviews) to match readers with books based on story structure rather than genre tags or collaborative filtering.

Built for ECE 464.

---

## What it does

- **"More like this"** similarity based on shared story structure (tropes + archetypes)
- **Personalized recommendations** derived from a user's rating and shelf history
- **Semantic vibe search** — understands "cozy mystery with slow-burn romance" as a query
- **Hybrid search** combining full-text keyword matching with semantic description similarity via Reciprocal Rank Fusion
- **Social layer** — follow other readers, activity feed, public shelves
- **User tagging** — readers annotate books with tropes/archetypes; tags crowd-promote to canonical at ≥ 3 users

---

## Current State

| Area | Status |
|---|---|
| Backend API | Feature-complete |
| Database schema | Stable (26 migrations) |
| Embedding pipeline | Three-stream BGE (genome 384d, description 768d, review 768d) |
| Search | Vibe/semantic + hybrid RRF |
| Recommendations | Personalized + similar books |
| Social / friends | Follow system, activity feed, public profiles |
| User preferences | Content blocklist, privacy toggle |
| Frontend | Feature-complete |
| Admin dashboard | Embed pipeline, cover fetching, vector coverage panel |
| Crowd promotion | User tags promote to canonical at ≥ 3 users |
| Auth | Supabase JWT |
| E2E Testing | 57 Playwright tests — 56 pass, 1 skip |
| Data | 648 tagged books live; ~5,772 total in DB |

See [FEATURES.md](FEATURES.md) for the full feature reference, API documentation, and architecture details.

---

## Tech Stack

### Backend
| Tool | Role |
|---|---|
| Python 3.12 + FastAPI | API framework |
| SQLAlchemy 2.0 (async) + asyncpg | ORM + Postgres driver |
| Alembic | DB migrations |
| pgvector | Vector similarity in Postgres |
| FastEmbed (BAAI/bge) | Local BGE embedding models |
| Supabase | Auth (JWT) + Postgres hosting |

### Frontend
| Tool | Role |
|---|---|
| React 19 + TypeScript | UI framework |
| Vite | Build tool |
| React Router v7 | Client-side routing (data router) |
| Supabase JS | Auth client |
| Tailwind CSS | Styling |

---

## Repository Structure

```
CommonThread/
├── README.md
├── FEATURES.md             ← Full feature reference + API docs
├── error_log.md            ← Dev error log
├── e2e/                    ← Playwright end-to-end tests
│   ├── tests/              # 11 spec files, 57 tests
│   ├── global-setup.ts     # Magic-link auth setup
│   └── playwright.config.ts
├── backend/
│   ├── app/
│   │   ├── main.py         # FastAPI app, lifespan, CORS
│   │   ├── auth.py         # Supabase JWT validation
│   │   ├── models/         # SQLAlchemy ORM models
│   │   ├── schemas/        # Pydantic request/response schemas
│   │   ├── routers/        # API route handlers (15 modules)
│   │   ├── crud/           # Data access layer
│   │   └── services/       # Embedding, similarity, cover fetching
│   ├── migrations/         # Alembic migration history
│   ├── scripts/            # seed, import_tagged_books, embed_all
│   ├── webscraper/         # Open Library async scraper
│   ├── parse_books.md      # Book tagging workflow + resumption guide
│   └── reference_data.md   # Taxonomy reference (tropes, archetypes, genres, etc.)
└── frontend/
    └── src/
        ├── api/            # Typed API client (client.ts)
        ├── contexts/       # AuthContext, ToastContext
        ├── components/     # ProtectedRoute, RatingModal, ReadingStatusButton, ConfirmModal
        └── pages/          # Route page components
```

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
cp .env.example .env   # fill in TEST_EMAIL, ADMIN_EMAIL, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY

npm test                              # all 57 tests
npx playwright test --project=public  # 14 public tests — no credentials needed
npx playwright test --ui              # interactive UI mode
```

See [FEATURES.md — End-to-End Testing](docs/FEATURES.md#end-to-end-testing) for full test coverage details.
