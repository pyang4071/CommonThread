# CommonThread

A book recommendation engine powered by tropes and character archetypes. CommonThread models books at the level of narrative DNA — tropes and archetypes with weighted importance — and uses a three-stream semantic embedding approach (structural genome, prose description, aggregated reviews) to match readers with books based on story structure rather than genre tags or collaborative filtering.

Built for ECE 464.

---

## What it does

- **"More like this"** similarity based on shared story structure (tropes + archetypes)
- **Personalized recommendations** derived from a user's rating and shelf history
- **Hybrid search** — understands "cozy mystery with slow-burn romance" as a query; combines full-text keyword matching with semantic description similarity via Reciprocal Rank Fusion
- **Social layer** — follow other readers, activity feed, public shelves
- **User tagging** — readers annotate books with tropes/archetypes; tags crowd-promote to canonical at ≥ 3 users

---

## Current State

| Area | Status |
|---|---|
| Backend API | Feature-complete |
| Database schema | Stable (26 migrations) |
| Embedding pipeline | Three-stream BGE (genome 384d, description 768d, review 768d) |
| Search | Hybrid RRF (lexical + semantic) |
| Recommendations | Personalized + similar books |
| Social / friends | Follow system, activity feed, public profiles |
| User preferences | Content blocklist, privacy toggle |
| Frontend | Feature-complete |
| Admin dashboard | Embed pipeline, cover fetching, vector coverage panel |
| Crowd promotion | User tags promote to canonical at ≥ 3 users |
| Auth | Supabase JWT |
| E2E Testing | 57 Playwright tests — 56 pass, 1 skip |
| Data | 648 tagged books live; ~5,772 total in DB |

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
├── SETUP.md                ← Local dev, Docker, and deployment guide
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

## Docs

- [FEATURES.md](FEATURES.md) — full feature reference, API documentation, and architecture details
- [SETUP.md](SETUP.md) — local development, environment variables, Docker, Railway + Vercel deployment
