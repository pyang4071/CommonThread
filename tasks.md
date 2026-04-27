# CommonThread — Task Tracker

---

## Pre-Deployment

### 🔴 Blockers

- [x] **Audit `lazy="raise"` additions** *(2026-04-27)*
  Audited all routes. `BookRead` (list endpoint) does not include `book_tropes`/`character_dna` — only `BookReadDetail` does, and that always uses `get_book_detail()` which has full `selectinload` chains. The recommendations CRUD uses raw SQL joins, not ORM relationship traversal. Changes are safe.

- [x] **Fix `client.ts` BASE URL for Railway + Vercel deployment** *(2026-04-27)*
  Updated to `import.meta.env.VITE_API_BASE_URL ? .../api/v1 : /api/v1`. Added `VITE_API_BASE_URL` build arg to `frontend/Dockerfile` and `frontend/.env.example`.

- [x] **Create `frontend/vercel.json`** *(2026-04-27)*
  Created with SPA routing (`/(.*) → /index.html`) and API proxy (`/api/:path* → Railway`). **Requires manual update:** replace `<your-railway-service>` placeholder with the actual Railway service URL before deploying.

- [x] **Fix `UserFollow` UniqueConstraint discrepancy** *(2026-04-27)*
  Restored `UniqueConstraint("follower_id", "followee_id", name="uq_user_follows")` to the model. The constraint was created by the `l6m7n8o9p0q1` migration and exists in the DB; model must match to avoid autogenerate drift.

- [ ] **Commit all pending changes and apply index migration** *(manual — requires DB access)*
  Commit: model changes (book.py, book_trope.py, character_dna.py, book_rating.py, reading_status.py, user_follow.py, crud/book.py), new migration `r2s3t4u5v6w7_add_query_indexes.py`, new test files, vercel.json, client.ts, Dockerfile, README, .env.example, tasks.md.
  Then apply against the production DB:
  ```bash
  cd backend && uv run alembic upgrade head
  ```

---

### 🟡 Important

- [x] **Fix `ReadingStatus.updated_at` — add `onupdate`** *(in pending model diff)*
  `onupdate=func.now()` added to `ReadingStatus.updated_at`. ORM-level only — no migration needed. Will be applied when the pending changes are committed.

---

### 🟢 Environment Config — manual steps before first deploy

- [ ] **Set Railway environment variables**
  In the Railway dashboard for the backend service, set:
  ```
  SUPABASE_URL=https://<ref>.supabase.co
  SUPABASE_ANON_KEY=<anon-key>
  SUPABASE_SERVICE_ROLE_KEY=<service-role-key>
  DATABASE_URL=postgresql+asyncpg://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres
  SECRET_KEY=<output of: openssl rand -hex 32>
  ENVIRONMENT=production
  CORS_ORIGINS=["https://<your-vercel-domain>.vercel.app"]
  CROWD_PROMOTION_THRESHOLD=3
  ```

- [ ] **Set Vercel environment variables**
  In the Vercel dashboard for the frontend project, set:
  ```
  VITE_SUPABASE_URL=https://<ref>.supabase.co
  VITE_SUPABASE_ANON_KEY=<anon-key>
  VITE_API_BASE_URL=https://<your-railway-service>.up.railway.app
  ```

- [ ] **Update `frontend/vercel.json` with actual Railway URL**
  Replace the `<your-railway-service>` placeholder in `frontend/vercel.json` with the real Railway service hostname once it is provisioned.

- [ ] **Add Railway persistent volume for FastEmbed cache**
  In Railway service settings, mount a volume at `/root/.cache/fastembed` so the ~570 MB BGE models are not re-downloaded on every redeploy.

---

## Remaining Data Work

- [ ] **Tag the remaining ~9,200 scraped books**
  Only 648 of ~5,772 DB books have tropes/archetypes. The rest are invisible in vibe search, Similar Books, and For You recommendations. See `create_books.md` for the AI tagging workflow and `backend/webscraper/output/tagging_progress.json` for the checkpoint.

---

## Code Quality

- [x] **Expand backend unit tests** *(2026-04-27)*
  Added `test_auth.py` (12 tests), `test_follow.py` (14 tests), `test_genome_builder.py` (31 tests). Fixed 2 stale pre-existing failures. Total: 120 tests passing.

- [ ] **Add `pytest-cov` and set a coverage floor**
  Install `pytest-cov` in the `dev` dependency group and add `--cov-fail-under=70` to CI.
