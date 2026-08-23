# CommonThread

A book recommendation engine that matches readers by narrative DNA — tropes and character archetypes — instead of genre tags or collaborative filtering.


**135 Playwright end-to-end tests** across 13 spec files (public / user / admin projects) cover auth, search, tagging, recommendations, the social layer, and the admin dashboard — see [docs/features.md](docs/features.md#end-to-end-testing).

---

## Stack

**Backend:** Python 3.12 + FastAPI, SQLAlchemy 2.0 (async) + asyncpg, Alembic migrations, pgvector for similarity search, FastEmbed (BAAI/bge) for local embeddings, Supabase for auth + Postgres hosting.
**Frontend:** React 19 + TypeScript on Vite, React Router v7 (data router), Supabase JS for auth, Tailwind CSS.

---

## What it does

- **"More like this"** similarity based on shared story structure (tropes + archetypes)
- **Personalized recommendations** derived from a user's rating and shelf history
- **Hybrid search** — understands "cozy mystery with slow-burn romance" as a query; combines full-text keyword matching with semantic description similarity via Reciprocal Rank Fusion
- **Social layer** — follow other readers, activity feed, public shelves
- **User tagging** — readers annotate books with tropes/archetypes; tags crowd-promote to canonical at ≥ 3 users

---

## Current State

Backend and frontend are feature-complete: hybrid RRF search, a three-stream BGE embedding pipeline (genome 384d, description 768d, review 768d), personalized + similar-book recommendations, a social layer (follows, activity feed, public profiles), crowd-promoted tagging, Supabase-JWT auth, and an admin dashboard for the embedding pipeline, cover fetching, and vector coverage. The schema is stable across 32 migrations; ~887 of ~5,777 books in the DB are fully tagged.

---

## Docs

- [docs/features.md](docs/features.md) — full feature reference, API documentation, and architecture details
- [docs/schema.md](docs/schema.md) — database schema: every table and column explained
- [docs/search_and_recommendations.md](docs/search_and_recommendations.md) — how search and recommendations work
- [SETUP.md](SETUP.md) — local development, environment variables, Docker, and deployment

---

## Repository Structure

<details>
<summary>Expand tree</summary>

```
CommonThread/
├── README.md
├── SETUP.md                ← Local dev, Docker, and deployment guide
├── docs/
│   ├── features.md         ← Full feature reference + API docs
│   ├── schema.md           ← Database schema — every table and column explained
│   ├── search_and_recommendations.md  ← Search and recommendation system deep-dive
│   └── error_log.md        ← Dev error log
├── e2e/                    ← Playwright end-to-end tests
│   ├── tests/              # 13 spec files, 135 tests
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

</details>

---

Final project for ECE 464 — Databases.
