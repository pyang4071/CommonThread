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
**Status:** [x] done

---

### T-06 Confirm before Dislike
**Problem:** The 👎 Dislike button has no confirmation. It's easy to misclick — especially next to the reading status button — and the dislike permanently affects recommendations.  
**Fix:** Clicking 👎 when not already disliked now opens a `ConfirmModal` explaining the consequence. Confirming calls `toggleDislike`. Removing the dislike (clicking again when already disliked) skips the modal — no confirmation needed to undo. Dislike button also shows a spinner while in-flight and toasts on error.  
**Files affected:** `BookDetail.tsx`.  
**Status:** [x] done

---

### T-18 Confirm before delete on Books card grid
**Problem:** The admin Delete button on each book card in `Books.tsx` calls `remove(b)` directly with no confirmation. Every other destructive action in the app (dislike, tag remove in `Table`) uses a `ConfirmModal`. This is a regression introduced when the `<Table>` component (which handled confirm internally) was replaced with the card grid in T-09.  
**Fix:** Wrap `onClick={() => remove(b)}` with the existing `ConfirmModal` — same pattern used by the Dislike button in `BookDetail.tsx`. Add a `[bookToDelete, setBookToDelete]` state, render the modal, and call `remove` on confirm.  
**Files affected:** `Books.tsx`.  
**Status:** [x] done

---

### T-19 Admin-only Edit button on BookDetail
**Problem:** The "Edit" button in `BookDetail.tsx` is visible to every logged-in user and navigates to `/books/:id/edit`. The edit route has `<ProtectedRoute>` but not `adminOnly`, meaning any authenticated user can reach the edit form. This exposes full book metadata editing (tropes, archetypes, weights) to the public.  
**Fix:** Destructure `isAdmin` from `useAuth()` in `BookDetail.tsx` and conditionally render the Edit button only when `isAdmin` is true. Optionally also add `adminOnly` to the `/books/:id/edit` route in `App.tsx`.  
**Files affected:** `BookDetail.tsx`, `App.tsx`.  
**Status:** [x] done

---

### T-20 Keyboard navigation for Profile BlocklistPicker
**Problem:** `Profile.tsx` has its own `BlocklistPicker` component — a typeahead for blocking genres, book types, and tones — that was not included in T-08. It has no `ArrowUp`/`ArrowDown`/`Enter`/`Escape` keyboard handling, making it mouse-only.  
**Fix:** Apply the same `highlightedIndex` pattern implemented in `ChipPicker` (Books.tsx) during T-08: add `highlightedIndex` state, `useRef` for the list, scroll-into-view effect, `onKeyDown` handler, `onMouseEnter` sync, and conditional highlight class.  
**Files affected:** `Profile.tsx`.  
**Status:** [x] done

---

### T-27 Confirm before removing a personal tag in MyTags
**Problem:** The ✕ button on each tag in `MyTags.tsx` calls `handleRemoveTrope` / `handleRemoveArchetype` immediately with no confirmation. Every other destructive action in the app uses a `ConfirmModal`. A misclick silently deletes a tag that influences recommendations.  
**Fix:** Wrap the ✕ `onClick` with a `ConfirmModal` (same pattern used by Dislike and Books delete). Store `tagToRemove` state as `{ type: 'trope'|'archetype', bookId, id, name }` and render a single modal at page level.  
**Files affected:** `MyTags.tsx`.  
**Status:** [ ] todo

---

### T-28 Fix "Want to Read" link on Home page
**Problem:** The "Browse →" link next to "N books on your want-to-read list" in `Home.tsx` navigates to `/books` (the browse page). The want-to-read list actually lives on `/shelf`. Users clicking it expect to see their queued books, not the full catalogue.  
**Fix:** Change `<Link to="/books">` to `<Link to="/shelf">` for that specific link.  
**Files affected:** `Home.tsx`.  
**Status:** [ ] todo

---

### T-29 Admin data pages (Genres, BookTypes, Tones) still use `<Table>`
**Problem:** `Genres.tsx`, `BookTypes.tsx`, and `Tones.tsx` are the last three pages using the `<Table>` component. They have no search/filter and no skeleton loading state. They're admin-only so lower traffic, but inconsistent with the rest of the app.  
**Fix:** Replace `<Table>` with a simple searchable list (inline filter input + item rows with name, description, and delete button). Add `animate-pulse` skeleton loading. No card grid needed — a dense list layout suits small reference datasets better.  
**Files affected:** `Genres.tsx`, `BookTypes.tsx`, `Tones.tsx`.  
**Status:** [ ] todo

---

### T-30 Success feedback after adding or editing a book
**Problem:** `AddBook.tsx` navigates to the new book's detail page on success but shows no toast. `EditBook.tsx` navigates back to the book but also shows no success confirmation. The user has no explicit acknowledgment that their save worked.  
**Fix:** Fire `toast.success('Book added.')` just before `navigate(...)` in `AddBook.tsx`, and `toast.success('Changes saved.')` in `EditBook.tsx`. Both pages already import `useNavigate`; just add `useToast`.  
**Files affected:** `AddBook.tsx`, `EditBook.tsx`.  
**Status:** [ ] todo

---

## Tier 2 — High Impact, Medium Effort

### T-07 Loading skeletons on Shelf, Home, and MyTags
**Problem:** Shelf, Home ("For You" + Currently Reading), and MyTags all render empty white space while fetching. On slower connections this looks like a broken page.  
**Fix:** All three pages already had full `animate-pulse` skeleton loading states — no changes required.  
**Files affected:** `Home.tsx`, `Shelf.tsx`, `MyTags.tsx`.  
**Status:** [x] done (already implemented)

---

### T-08 Keyboard support for trope/archetype pickers
**Problem:** The trope and archetype search dropdowns in `AddBook.tsx` / `EditBook.tsx` and in `BookDetail.tsx`'s personal-tag section can only be used with a mouse. No arrow key navigation, no Enter to select, no Escape to close.  
**Fix:** Added `highlightedIndex` state with `ArrowUp`/`ArrowDown`/`Enter`/`Escape` handlers to `ChipPicker` in `Books.tsx`, and to the trope/archetype typeaheads in `AddBook.tsx` and `EditBook.tsx`. Mouse hover syncs with keyboard state via `onMouseEnter`. `scrollIntoView({ block: 'nearest' })` keeps highlighted item visible.  
**Files affected:** `Books.tsx`, `AddBook.tsx`, `EditBook.tsx`.  
**Status:** [x] done

---

### T-09 Standardize search and vibe-search result layouts
**Problem:** Keyword search returns a table; vibe/semantic search returns a card grid. Switching between them causes a jarring layout shift and different information density.  
**Fix:** Replaced `<Table>` with a `grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3` card grid for keyword/filter results, matching the vibe-search layout. Each card shows cover, title (linked), author, pub year, avg rating, `ReadingStatusButton`, and (admin only) a small Delete button. Skeleton replaced with card-shaped pulse placeholders.  
**Files affected:** `Books.tsx`.  
**Status:** [x] done

---

### T-10 Pagination: show result count and total pages
**Problem:** Pagination only shows "Page N" with previous/next. There is no total result count, no "Next" disabled state when on the last page, and no way to jump to a specific page.  
**Fix:** Used the existing `PAGE_SIZE + 1` fetch trick for last-page detection. Pagination now shows `"Page N · X–Y shown"` with `+` suffix if more exist. "Next" is disabled when `books.length <= PAGE_SIZE`. No backend change needed.  
**Files affected:** `Books.tsx`.  
**Status:** [x] done

---

### T-11 "Why this recommendation?" on Similar Books
**Problem:** The "Books Like This" section on BookDetail shows book cards but no explanation of why they match — unlike the "For You" section on Home which lists shared tropes/archetypes.  
**Fix:** Changed `sharedTags.join(' · ')` plain text to a `flex-wrap` row of small `bg-indigo-50 text-indigo-600 border-indigo-100` chip spans. The `explanation.shared_tropes` and `explanation.shared_archetypes` arrays were already typed and available.  
**Files affected:** `BookDetail.tsx`.  
**Status:** [x] done

---

### T-12 Sort and filter on Shelf
**Problem:** The shelf is a flat chronological grid with no sorting or filtering. Users with large shelves can't sort by title, rating, or date added.  
**Fix:** Added a sort `<select>` in the page header: "Date Added (newest)", "Date Added (oldest)", "Title A–Z". Applied via a `sortEntries()` helper (client-side, uses `ShelfEntry.created_at` and `book.title`). Sorts each section independently; dropdown only appears when shelf is non-empty.  
**Files affected:** `Shelf.tsx`.  
**Status:** [x] done

---

### T-21 Replace native `<select>` with typeahead for personal tag addition in BookDetail
**Problem:** The "Your Tags" section in `BookDetail.tsx` adds tropes/archetypes via a plain `<select>` element that lists every trope or archetype alphabetically (potentially hundreds of options). The same problem was solved for `AddBook.tsx` and `EditBook.tsx` — they use a text-input typeahead. The `BookDetail` version was not updated.  
**Fix:** Replace the trope `<select>` + `<input type="range">` add-row and archetype `<select>` + range row with the same typeahead pattern used in `AddBook.tsx`: text input, dropdown list filtered by query, keyboard nav (reuse the pattern from T-08), `onSelect` adds the tag and clears the input. Keep the weight/importance range slider after selection.  
**Files affected:** `BookDetail.tsx`.  
**Status:** [x] done

---

### T-22 Searchable card grid for Tropes and Archetypes list pages
**Problem:** `Tropes.tsx` and `Archetypes.tsx` both still render `<Table>` — the only remaining uses of that component. With potentially hundreds of tropes, the page is a long unfiltered table with no way to search by name or filter by category. The rows are also not clickable links to the detail pages.  
**Fix:** Replace `<Table>` with a filterable card grid (search input + optional category filter chip). Each card shows name, category badge (tropes), description snippet, and book count if available, and links to `/tropes/:id` or `/archetypes/:id`. Admin create form stays at the top. This makes `Table` importable only from admin-data pages.  
**Files affected:** `Tropes.tsx`, `Archetypes.tsx`.  
**Status:** [x] done

---

### T-23 Quick title-filter input on Shelf page
**Problem:** Users with large shelves have no way to find a specific book without scrolling through all sections. The sort added in T-12 helps with ordering but not with locating a single title.  
**Fix:** Add a small text input at the top of the shelf (below the sort control) that does a client-side case-insensitive filter on `book.title` and `book.author.name`. When the filter is active, all three sections still appear but only show matching entries; sections with zero matches are hidden. Clear button resets the filter.  
**Files affected:** `Shelf.tsx`.  
**Status:** [x] done

---

### T-31 MyTags search / filter
**Problem:** With many tagged books, `MyTags.tsx` is an unfiltered grid with no way to find a specific book or tag. Users who actively tag books will outgrow the current flat grid quickly.  
**Fix:** Add a text input above the grid that filters `entries` by `book.title`, `book.author.name`, or any trope/archetype name in the entry's tag lists (all client-side). Show a count of matching books. Clear button resets the filter.  
**Files affected:** `MyTags.tsx`.  
**Status:** [ ] todo

---

### T-32 Star hover preview in RatingModal
**Problem:** The rating stars in `RatingModal.tsx` are clickable but show no hover state — hovering over star 3 doesn't preview a 3-star rating. This makes it hard to tell which star you're about to click.  
**Fix:** Add a `hoverRating` state (number | null). On `onMouseEnter` for each star set `hoverRating = i`, on `onMouseLeave` clear it. Render filled stars up to `hoverRating ?? currentRating` so the preview is visible while hovering.  
**Files affected:** `RatingModal.tsx`.  
**Status:** [ ] todo

---

### T-33 Review sort controls on BookDetail
**Problem:** Reviews in `BookDetail.tsx` are shown in the order returned by the API with no way to re-sort. Users with many reviews can't find the most recent or highest-rated ones.  
**Fix:** Add a small sort `<select>` above the review list: "Newest first", "Oldest first", "Highest rating", "Lowest rating". Apply as a client-side sort on the `reviews` array. Only show the control when there are 2+ reviews.  
**Files affected:** `BookDetail.tsx`.  
**Status:** [ ] todo

---

## Tier 3 — Polish

### T-13 Smooth panel open/close transitions
**Problem:** Filter panel and vibe search panel on Books page appear/disappear instantly, causing content to jump.  
**Fix:** Added `@keyframes panel-in` (opacity 0→1, translateY -6px→0, 0.18s ease-out) to `index.css` and applied `.animate-panel-in` class to both panels. Panels fade+slide in smoothly on open.  
**Files affected:** `src/index.css`, `Books.tsx`.  
**Status:** [x] done

---

### T-14 "Back to top" button on BookDetail
**Problem:** BookDetail is very long (tropes → archetypes → personal tags → series → reviews → similar books). No way to get back to the top without scrolling.  
**Fix:** Added `showBackToTop` state with a passive `scroll` listener (`window.scrollY > 300`). Renders a fixed bottom-right `"↑ Top"` pill button that scrolls to top smoothly on click. Uses `animate-panel-in` for entrance.  
**Files affected:** `BookDetail.tsx`.  
**Status:** [x] done

---

### T-15 Breadcrumb / context indicator on detail pages
**Problem:** TropeDetail and ArchetypeDetail only have a "← Tropes" back link. BookDetail shows "← Back to Books" or "← Back to Shelf" depending on navigation source. Users lose context if they open a detail page in a new tab or reload.  
**Fix:** Replaced the back link with a `<nav>` breadcrumb bar: `Tropes › Name` / `Archetypes › Name` / `Books › Title` (or `My Shelf › Title`). The parent segment is a clickable link; the current page name is plain gray text with `truncate`.  
**Files affected:** `TropeDetail.tsx`, `ArchetypeDetail.tsx`, `BookDetail.tsx`.  
**Status:** [x] done

---

### T-16 Explain Personal Tags to new users
**Problem:** The "Your Tags" section on BookDetail and the entire MyTags page have no explanation of why they exist or how they influence recommendations.  
**Fix:** Updated the "Your Tags" section description in `BookDetail.tsx` to the full callout sentence. Added an `indigo-50` callout banner below the heading on `MyTags.tsx` with the same message.  
**Files affected:** `BookDetail.tsx`, `MyTags.tsx`.  
**Status:** [x] done

---

### T-17 Character count on review textarea
**Problem:** The review text input in RatingModal has no visible length limit. The backend schema has no constraint either, but very long reviews would be jarring in the UI.  
**Fix:** Added `maxLength={1000}` to the textarea and a `"N / 1000"` counter aligned to the right of the label. Counter turns amber when over 900 characters as a soft warning.  
**Files affected:** `RatingModal.tsx`.  
**Status:** [x] done

---

### T-24 Responsive / collapsible nav for mobile
**Problem:** The `Header` in `App.tsx` renders all nav links as a flat flex row. On screens narrower than ~900px the links overflow the header and become inaccessible or wrap in an ugly way. The app has no mobile-friendly navigation.  
**Fix:** Add a hamburger button (visible at `md:hidden`) that toggles a dropdown menu showing all nav links as a vertical list. On `md:` and wider, the original horizontal nav shows and the hamburger is hidden. Use a simple `menuOpen` boolean state and `animate-panel-in` for the dropdown entrance.  
**Files affected:** `App.tsx`.  
**Status:** [x] done

---

### T-25 UserProfile page breadcrumb
**Problem:** `UserProfile.tsx` hardcodes `← Back to Friends` as its back link. If a user lands on a profile page from the activity feed, search results, or a direct URL, the link is misleading. Pattern is inconsistent with T-15 changes made to other detail pages.  
**Fix:** Replace the back link with a `<nav>` breadcrumb bar: `Friends › Display Name`. Parent "Friends" is a `<Link to="/friends">`. Current user's name is plain text with `truncate`.  
**Files affected:** `UserProfile.tsx`.  
**Status:** [x] done

---

### T-26 Admin page auto-refresh during embedding
**Problem:** After clicking "Embed All" in `Admin.tsx`, the embed status refreshes once after an 800ms delay and then stops. There is no way to watch live progress without manually navigating away and back or clicking a refresh. For large libraries this means flying blind.  
**Fix:** After a successful `handleEmbedAll` kick-off, start a polling interval (every 4 s) that calls `loadStatus()`. Stop the interval when `status.pending === 0` or when the component unmounts. Show a "Refreshing…" badge next to the status bar while polling is active.  
**Files affected:** `Admin.tsx`.  
**Status:** [x] done

---

### T-34 Dynamic browser tab title per page
**Problem:** Every page shows the same generic browser tab title. Users with multiple tabs open can't distinguish them, and bookmarked pages have no useful label.  
**Fix:** Add `useEffect(() => { document.title = '...' }, [...])` to each page component. Format: `"Page Name — CommonThread"` for top-level pages, `"Item Name · Section — CommonThread"` for detail pages. Reset to `"CommonThread"` on the Home page.  
**Files affected:** `Home.tsx`, `Books.tsx`, `BookDetail.tsx`, `Shelf.tsx`, `MyTags.tsx`, `Tropes.tsx`, `TropeDetail.tsx`, `Archetypes.tsx`, `ArchetypeDetail.tsx`, `Friends.tsx`, `Profile.tsx`, `Admin.tsx`.  
**Status:** [ ] todo

---

### T-35 Relative timestamps in Friends activity feed
**Problem:** Feed items in `Friends.tsx` show an absolute date like "Apr 10". For recent activity (today, yesterday, 2 days ago) a relative label is far more useful and natural.  
**Fix:** Add a small `relativeTime(date: Date): string` helper that returns "Today", "Yesterday", "N days ago" for the past week, then falls back to the existing `toLocaleDateString` format for older entries. Apply to `FeedItem` in `Friends.tsx` and the feed strip on `Home.tsx`.  
**Files affected:** `Friends.tsx`, `Home.tsx`.  
**Status:** [ ] todo

---

### T-36 Compact hero for logged-in users on Home
**Problem:** The hero section (`<div className="text-center py-12">`) occupies 100+ px of vertical space with the app name and tagline — information logged-in users don't need. It pushes the "Currently Reading" shelf and recommendations below the fold.  
**Fix:** When `session` is truthy, render a compact one-line greeting (`"Good morning, [name]"` or just hide the hero entirely) instead of the full centred hero. The full hero stays for logged-out visitors.  
**Files affected:** `Home.tsx`.  
**Status:** [ ] todo

---

## Done

- [x] T-01 Global toast/snackbar system — `src/contexts/ToastContext.tsx`, `App.tsx`
- [x] T-02 Loading states on async buttons — `ReadingStatusButton.tsx`, `BookDetail.tsx`
- [x] T-03 Active filter summary bar — `Books.tsx`
- [x] T-04 Vibe Search explanation + example prompts — `Books.tsx`
- [x] T-05 Empty state for Similar Books — `BookDetail.tsx` (`similarLoaded` flag, dashed empty card, admin link to /admin)
- [x] T-06 Confirm before Dislike — `BookDetail.tsx`
- [x] T-07 Loading skeletons — already existed in `Home.tsx`, `Shelf.tsx`, `MyTags.tsx`
- [x] T-08 Keyboard nav for pickers — `Books.tsx` (`ChipPicker`), `AddBook.tsx`, `EditBook.tsx`
- [x] T-09 Card grid for keyword results — `Books.tsx` (removed `<Table>`)
- [x] T-10 Pagination range display — `Books.tsx` (Page N · X–Y shown)
- [x] T-11 Shared-tag chips on similar books — `BookDetail.tsx`
- [x] T-12 Sort controls on Shelf — `Shelf.tsx` (title / date added)
- [x] T-13 Panel open animations — `index.css` (`@keyframes panel-in`), `Books.tsx`
- [x] T-14 Back-to-top button on BookDetail — `BookDetail.tsx`
- [x] T-15 Breadcrumbs on detail pages — `TropeDetail.tsx`, `ArchetypeDetail.tsx`, `BookDetail.tsx`
- [x] T-16 Personal tags explanation — `BookDetail.tsx`, `MyTags.tsx`
- [x] T-17 Review character count — `RatingModal.tsx`
- [x] T-18 Confirm before delete on Books card grid — `Books.tsx` (`ConfirmModal`)
- [x] T-19 Admin-only Edit button on BookDetail — `BookDetail.tsx`, `App.tsx` (`adminOnly` route)
- [x] T-20 Keyboard nav for Profile BlocklistPicker — `Profile.tsx`
- [x] T-21 Typeahead for personal tag addition in BookDetail — `BookDetail.tsx`
- [x] T-22 Searchable card grid for Tropes and Archetypes — `Tropes.tsx`, `Archetypes.tsx`
- [x] T-23 Title/author filter on Shelf — `Shelf.tsx`
- [x] T-24 Responsive hamburger nav — `App.tsx` (md breakpoint, `animate-panel-in`)
- [x] T-25 UserProfile breadcrumb — `UserProfile.tsx`
- [x] T-26 Admin auto-refresh during embedding — `Admin.tsx` (4 s polling, "Refreshing…" badge)
- [x] Supabase credentials moved to `VITE_*` env vars (`frontend/.env.local`, `.env.example`)
- [x] Cover fetch retry logic (3 attempts, exponential back-off) — `services/covers.py`
- [x] FastEmbed model pre-warm in lifespan — `main.py`
- [x] Production CORS `CORS_ORIGINS` setting — `config.py`
- [x] Docker Compose deployment config — `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`
- [x] Profile page with name edit + content blacklist (blocked genres/types/tones) — `Profile.tsx`, `UserPreferences` schema, JSONB migration `k5l6m7n8o9p0`
- [x] `profile_public` privacy toggle on profile page — stored in `preferences` JSONB, toggle switch in Profile UI
- [x] Admin-only nav links hidden from standard users — `ProtectedRoute` `adminOnly` prop, `App.tsx`
- [x] Friends / follow system — `user_follows` table (migration `l6m7n8o9p0q1`), follow/unfollow/search endpoints, activity feed, `Friends.tsx` page, `UserProfile.tsx` page, friend strip on `Home.tsx`
