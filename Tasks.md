# CommonThread — UX Task List

Prioritized improvements identified from a full read of `frontend/src/`. Items are grouped by impact tier; within each tier they are roughly ordered by effort (low → high).

---

## Tier 1 — High Impact, Low Effort

### T-01 Global toast / snackbar system
**Problem:** Async operations (rating saved, tag added, status changed, dislike toggled) either fail silently or show inline red alert boxes inconsistently across every page.  
**Fix:** Added `ToastContext.tsx` with `ToastProvider`, `useToast` hook, and inline `Toaster` component (fixed bottom-right, auto-dismiss 3 s success / 5 s error). Wired into `App.tsx` wrapping `AuthProvider`.  
**Files affected:** `src/contexts/ToastContext.tsx` (new), `App.tsx`.  
**Status:** [x] done

---

### T-02 Loading state on all async buttons
**Problem:** Buttons that trigger API calls (ReadingStatusButton, RatingModal save, dislike button, tag add/remove, admin embed-all, admin fetch-covers) have no spinner or visual change while in-flight. Users can multi-click and fire duplicate requests.  
**Fix:** `ReadingStatusButton` now has a `loading` state that disables the trigger and shows an inline CSS spinner while the API call is in-flight; reverts optimistically on failure and fires `toast.error`. `BookDetail` tag add/remove and dislike now use `toast.error` on failure and `toast.success` on successful tag adds. Note: `RatingModal` and `Admin` already had `saving`/`running` states — their error display is inline text which is acceptable.  
**Files affected:** `ReadingStatusButton.tsx`, `BookDetail.tsx`.  
**Status:** [x] done

---

### T-03 Active filter summary on Books page
**Problem:** After applying filters, there is no indication of how many results are showing or which filters are active unless you re-open the filter panel.  
**Fix:** Added a summary line below the search bar row. Shows "N books · X filters active" for keyword/filtered results, "N vibe results for '…'" for semantic results, and "Loading…" while fetching. Appears only when there is something to report.  
**Files affected:** `Books.tsx`.  
**Status:** [x] done

---

### T-04 Explain Vibe Search
**Problem:** The alpha slider (0–1, "Structure ↔ Vibe") is meaningless to most users. No example queries, no description of what it does differently from keyword search.  
**Fix:** Added `title` tooltip to the Vibe Search button with a plain-language explanation. Rewrote panel description. Added 4 clickable example-prompt chips that populate the input on click. Relabeled slider ends to "More vibe & prose" / "More tropes & archetypes".  
**Files affected:** `Books.tsx`.  
**Status:** [x] done

---

### T-05 Empty state for Similar Books
**Problem:** If `/recommendations/{id}/similar` returns an empty array, the "Books Like This" section on BookDetail just disappears with no message, leaving a confusing gap.  
**Fix:** Render `"No similar books found yet — this book may not be embedded."` with a note to check the Admin panel if the user is an admin.  
**Files affected:** `BookDetail.tsx`.  
**Status:** [ ] todo

---

### T-06 Confirm before Dislike
**Problem:** The 👎 Dislike button has no confirmation. It's easy to misclick — especially next to the reading status button — and the dislike permanently affects recommendations.  
**Fix:** Clicking 👎 when not already disliked now opens a `ConfirmModal` explaining the consequence. Confirming calls `toggleDislike`. Removing the dislike (clicking again when already disliked) skips the modal — no confirmation needed to undo. Dislike button also shows a spinner while in-flight and toasts on error.  
**Files affected:** `BookDetail.tsx`.  
**Status:** [x] done

---

## Tier 2 — High Impact, Medium Effort

### T-07 Loading skeletons on Shelf, Home, and MyTags
**Problem:** Shelf, Home ("For You" + Currently Reading), and MyTags all render empty white space while fetching. On slower connections this looks like a broken page.  
**Fix:** Add a simple `<SkeletonCard>` component (gray animated pulse div) and render N placeholders while `loading === true` for the main data fetch on each page.  
**Files affected:** `Home.tsx`, `Shelf.tsx`, `MyTags.tsx`.  
**Status:** [ ] todo

---

### T-08 Keyboard support for trope/archetype pickers
**Problem:** The trope and archetype search dropdowns in `AddBook.tsx` / `EditBook.tsx` and in `BookDetail.tsx`'s personal-tag section can only be used with a mouse. No arrow key navigation, no Enter to select, no Escape to close.  
**Fix:** Add `onKeyDown` handlers to each picker's input: `ArrowDown`/`ArrowUp` to move highlight, `Enter` to select highlighted item, `Escape` to close dropdown. Track `highlightedIndex` in local state.  
**Files affected:** `AddBook.tsx`, `EditBook.tsx`, `BookDetail.tsx`.  
**Status:** [ ] todo

---

### T-09 Standardize search and vibe-search result layouts
**Problem:** Keyword search returns a table; vibe/semantic search returns a card grid. Switching between them causes a jarring layout shift and different information density.  
**Fix:** Unify on the card-grid layout for both modes. The semantic card layout is already richer (cover + description preview + score badge); extend it to keyword results. Remove the separate table rendering for keyword results.  
**Files affected:** `Books.tsx`.  
**Status:** [ ] todo

---

### T-10 Pagination: show result count and total pages
**Problem:** Pagination only shows "Page N" with previous/next. There is no total result count, no "Next" disabled state when on the last page, and no way to jump to a specific page.  
**Fix:** Track total count from the API (or infer from `books.length < PAGE_SIZE` for last-page detection). Show `"Page 2 of 7 · 142 results"`. Disable "Next" on the last page.  
**Files affected:** `Books.tsx`.  
**Note:** May need a `GET /books/count` endpoint or add `total` to the list response schema.  
**Status:** [ ] todo

---

### T-11 "Why this recommendation?" on Similar Books
**Problem:** The "Books Like This" section on BookDetail shows book cards but no explanation of why they match — unlike the "For You" section on Home which lists shared tropes/archetypes.  
**Fix:** The `/recommendations/{id}/similar` endpoint already returns `matched_tropes` and `matched_archetypes` in its response. Surface these as small chips below the book title in the similar-books card.  
**Files affected:** `BookDetail.tsx`, `api/client.ts` (check if matched fields are typed).  
**Status:** [ ] todo

---

### T-12 Sort and filter on Shelf
**Problem:** The shelf is a flat chronological grid with no sorting or filtering. Users with large shelves can't sort by title, rating, or date added.  
**Fix:** Add a simple sort dropdown above each shelf section: `"Title A–Z"`, `"Date Added (newest)"`, `"My Rating"`. Sort is client-side on the already-fetched data.  
**Files affected:** `Shelf.tsx`.  
**Status:** [ ] todo

---

## Tier 3 — Polish

### T-13 Smooth panel open/close transitions
**Problem:** Filter panel and vibe search panel on Books page appear/disappear instantly, causing content to jump.  
**Fix:** Wrap panels in a `transition-all duration-200` Tailwind animation or a small CSS `max-height` transition.  
**Files affected:** `Books.tsx`.  
**Status:** [ ] todo

---

### T-14 "Back to top" button on BookDetail
**Problem:** BookDetail is very long (tropes → archetypes → personal tags → series → reviews → similar books). No way to get back to the top without scrolling.  
**Fix:** Add a fixed-position "↑ Top" button that appears after scrolling 300 px, using `window.scrollY` in a `useEffect`.  
**Files affected:** `BookDetail.tsx`.  
**Status:** [ ] todo

---

### T-15 Breadcrumb / context indicator on detail pages
**Problem:** TropeDetail and ArchetypeDetail only have a "← Tropes" back link. BookDetail shows "← Back to Books" or "← Back to Shelf" depending on navigation source. Users lose context if they open a detail page in a new tab or reload.  
**Fix:** Add a small breadcrumb bar: `Tropes › Enemies to Lovers` and `Books › The Midnight Library`. Static text derived from the loaded entity name.  
**Files affected:** `TropeDetail.tsx`, `ArchetypeDetail.tsx`, `BookDetail.tsx`.  
**Status:** [ ] todo

---

### T-16 Explain Personal Tags to new users
**Problem:** The "Your Tags" section on BookDetail and the entire MyTags page have no explanation of why they exist or how they influence recommendations.  
**Fix:** Add a one-sentence callout: *"Your tags are combined with system tropes to build your taste profile — they're how you tell the recommendation engine what actually resonated with you in this book."*  
**Files affected:** `BookDetail.tsx`, `MyTags.tsx`.  
**Status:** [ ] todo

---

### T-17 Character count on review textarea
**Problem:** The review text input in RatingModal has no visible length limit. The backend schema has no constraint either, but very long reviews would be jarring in the UI.  
**Fix:** Add a soft `maxLength={1000}` and a `"N / 1000"` counter in the bottom-right corner of the textarea.  
**Files affected:** `RatingModal.tsx`.  
**Status:** [ ] todo

---

## Done

- [x] T-01 Global toast/snackbar system — `src/contexts/ToastContext.tsx`, `App.tsx`
- [x] T-02 Loading states on async buttons — `ReadingStatusButton.tsx`, `BookDetail.tsx`
- [x] T-03 Active filter summary bar — `Books.tsx`
- [x] T-04 Vibe Search explanation + example prompts — `Books.tsx`
- [x] T-06 Confirm before Dislike — `BookDetail.tsx`
- [x] Supabase credentials moved to `VITE_*` env vars (`frontend/.env.local`, `.env.example`)
- [x] Cover fetch retry logic (3 attempts, exponential back-off) — `services/covers.py`
- [x] FastEmbed model pre-warm in lifespan — `main.py`
- [x] Production CORS `CORS_ORIGINS` setting — `config.py`
- [x] Docker Compose deployment config — `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`
