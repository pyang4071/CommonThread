"""
Goodreads ISBN-targeted enricher for CommonThread.

For each book already imported from Open Library (with a known ISBN), this
script looks up the book on Goodreads, scrapes user shelf names and review
texts, and writes the resulting data into CommonThread's database:

  1. Shelf names → canonical tropes (via SHELF_TO_TROPE mapping) written to
     `book_tropes` with `is_crowd_promoted = True` and a weight derived from
     shelf proportion.
  2. Review texts → aggregated into a single string and embedded into
     `books.review_embedding` via `embed_review_texts_directly`.

After trope writes, if a book's canonical trope count reaches TROPE_THRESHOLD
(3), a genome embedding is triggered.

Rate limiting
-------------
Goodreads is sensitive to scraping. We use a fixed 1.5 s delay + random jitter
(0–0.5 s) between each book, and back off exponentially on 429 / 503 responses.
This script is suitable for ECE 464 demonstration purposes only; it should NOT
be used in production.

Usage
-----
    cd backend
    uv run python webscraper/goodreads_enricher.py
    uv run python webscraper/goodreads_enricher.py --limit 50
    uv run python webscraper/goodreads_enricher.py --dry-run
    uv run python webscraper/goodreads_enricher.py --isbn 9780439023481
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import random
import re
import sys
from pathlib import Path
from typing import Optional

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import func, select, update

# Add backend root to sys.path so `app.*` imports resolve when run as a script.
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database.engine import AsyncSessionLocal
from app.models.book import Book
from app.models.book_trope import BookTrope
from app.models.trope import Trope
from app.services.embedding import embed_description_only, embed_book

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GOODREADS_SEARCH = "https://www.goodreads.com/search?q={isbn}&search_type=books"
GOODREADS_BOOK   = "https://www.goodreads.com{path}"

BASE_DELAY_S   = 1.5   # seconds between books
JITTER_MAX_S   = 0.5   # additional random delay
MAX_RETRIES    = 3
RETRY_BACKOFF  = 2.0   # base seconds; doubles each retry

MIN_SHELF_COUNT       = 200   # shelves below this are ignored (too noisy)
MIN_SHELF_PROPORTION  = 0.01  # shelf must be ≥ 1 % of total shelved count
MAX_SHELVES_PER_BOOK  = 10    # only consider the top-N shelves
MAX_REVIEWS_PER_BOOK  = 10    # top-N reviews to harvest

TROPE_THRESHOLD = 3   # mirrors user_tags.py constant

# ---------------------------------------------------------------------------
# Shelf name → canonical trope name mapping
#
# Keys are lowercased Goodreads shelf names (with hyphens normalised to spaces).
# Values are exact canonical trope names from reference_data.md.
# ---------------------------------------------------------------------------
SHELF_TO_TROPE: dict[str, str] = {
    # Romance
    "enemies to lovers":          "Enemies to Lovers",
    "enemies-to-lovers":          "Enemies to Lovers",
    "slow burn":                  "Slow Burn Romance",
    "slow-burn":                  "Slow Burn Romance",
    "slow burn romance":          "Slow Burn Romance",
    "forbidden love":             "Forbidden Love",
    "forbidden romance":          "Forbidden Love",
    "love triangle":              "Love Triangle",
    "fake dating":                "Fake Dating",
    "fake-dating":                "Fake Dating",
    "friends to lovers":          "Friends to Lovers",
    "friends-to-lovers":          "Friends to Lovers",
    "forced proximity":           "Forced Proximity",
    "forced-proximity":           "Forced Proximity",
    "second chance romance":      "Second Chance Romance",
    "second-chance-romance":      "Second Chance Romance",
    "grumpy sunshine":            "Grumpy × Sunshine",
    "grumpy-sunshine":            "Grumpy × Sunshine",
    "grumpy x sunshine":          "Grumpy × Sunshine",
    "marriage of convenience":    "Marriage of Convenience",
    "star-crossed lovers":        "Star-Crossed Lovers",
    "star crossed lovers":        "Star-Crossed Lovers",

    # Character
    "chosen one":                 "Chosen One",
    "chosen-one":                 "Chosen One",
    "coming of age":              "Coming of Age",
    "coming-of-age":              "Coming of Age",
    "redemption arc":             "Redemption Arc",
    "redemption-arc":             "Redemption Arc",
    "anti-hero":                  "Anti-Hero",
    "antihero":                   "Anti-Hero",
    "reluctant hero":             "Reluctant Hero",
    "fish out of water":          "Fish Out of Water",
    "fish-out-of-water":          "Fish Out of Water",
    "corrupted mentor":           "Corrupted Mentor",
    "villain protagonist":        "Villain Protagonist",

    # Narrative
    "unreliable narrator":        "Unreliable Narrator",
    "unreliable-narrator":        "Unreliable Narrator",
    "secret identity":            "Secret Identity",
    "revenge":                    "Revenge",
    "tragedy":                    "Tragedy",
    "in medias res":              "In Medias Res",
    "dual timeline":              "Dual Timeline",
    "dual-timeline":              "Dual Timeline",
    "twist ending":               "Twist Ending",
    "frame narrative":            "Frame Narrative",

    # Worldbuilding
    "magic system":               "Magic System",
    "magic-system":               "Magic System",
    "hidden world":               "Hidden World",
    "dark academia":              "Dark Academia",
    "dark-academia":              "Dark Academia",
    "post-apocalyptic":           "Post-Apocalyptic Setting",
    "post apocalyptic":           "Post-Apocalyptic Setting",
    "dystopia":                   "Dystopian Society",
    "dystopian":                  "Dystopian Society",
    "dystopian society":          "Dystopian Society",
    "secondary world":            "Secondary World",
    "soft magic":                 "Soft Magic",

    # Plot
    "found family":               "Found Family",
    "found-family":               "Found Family",
    "heist":                      "The Heist",
    "the heist":                  "The Heist",
    "political intrigue":         "Political Intrigue",
    "political-intrigue":         "Political Intrigue",
    "tournament":                 "Tournament / Competition",
    "competition":                "Tournament / Competition",
    "quest":                      "Quest",
    "prophecy":                   "Prophecy",
    "betrayal":                   "Betrayal",
    "forbidden knowledge":        "Forbidden Knowledge",
    "last stand":                 "Last Stand",
    "mistaken identity":          "Mistaken Identity",
    "reverse whodunit":           "Reverse Whodunit",

    # Mystery & Thriller
    "locked room mystery":        "Locked Room Mystery",
    "locked-room-mystery":        "Locked Room Mystery",
    "cold case":                  "Cold Case",
    "corrupt authority":          "Corrupt Authority",
    "the mole":                   "The Mole",
    "against the clock":          "Against the Clock",
    "conspiracy":                 "Conspiracy",

    # Horror & Gothic
    "haunted house":              "Haunted Setting",
    "haunted setting":            "Haunted Setting",
    "body horror":                "Body Horror",
    "psychological horror":       "Psychological Unreality",
    "psychological unreality":    "Psychological Unreality",
    "cosmic horror":              "Cosmic Horror",
    "gothic":                     "Gothic Atmosphere",
    "gothic atmosphere":          "Gothic Atmosphere",

    # Science Fiction
    "first contact":              "First Contact",
    "ai consciousness":           "AI Consciousness",
    "artificial intelligence":    "AI Consciousness",
    "time travel":                "Time Travel",
    "generation ship":            "Generation Ship",
    "human enhancement":          "Human Enhancement",
    "climate collapse":           "Climate Collapse",
    "climate fiction":            "Climate Collapse",
    "cli-fi":                     "Climate Collapse",
}


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


async def _get_html(
    client: httpx.AsyncClient,
    url: str,
    *,
    params: Optional[dict] = None,
) -> Optional[str]:
    """GET a URL and return the HTML text. Retries on transient errors / 429."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = await client.get(url, params=params)
            if resp.status_code == 404:
                return None
            if resp.status_code in (429, 503):
                wait = RETRY_BACKOFF ** attempt
                logger.warning(
                    "Rate limited (%s) on %s — waiting %.1f s (attempt %d/%d)",
                    resp.status_code, url, wait, attempt, MAX_RETRIES,
                )
                await asyncio.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.text
        except (httpx.TransportError, httpx.TimeoutException) as exc:
            logger.warning("Transport error on %s: %s (attempt %d/%d)", url, exc, attempt, MAX_RETRIES)
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_BACKOFF ** attempt)
    logger.error("All retries exhausted for %s", url)
    return None


# ---------------------------------------------------------------------------
# Goodreads parsing
# ---------------------------------------------------------------------------

def _find_book_path(html: str) -> Optional[str]:
    """
    From a Goodreads search results page, extract the href of the first book
    result (e.g. '/book/show/12345-my-book').
    Returns None if no result found.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Modern Goodreads: result rows are <tr> with class 'bookTitle'
    link = soup.select_one("a.bookTitle")
    if link and link.get("href"):
        return str(link["href"])

    # Fallback: any /book/show/ link in results
    for a in soup.find_all("a", href=re.compile(r"^/book/show/")):
        return str(a["href"])

    return None


def _parse_shelves(html: str) -> list[tuple[str, int]]:
    """
    Parse the community shelves section from a Goodreads book page.
    Returns a list of (shelf_name, count) pairs sorted by count descending.
    Only returns up to MAX_SHELVES_PER_BOOK entries.
    """
    soup = BeautifulSoup(html, "html.parser")
    results: list[tuple[str, int]] = []

    # Goodreads shelves live in a section with class 'communityShowcase' or
    # individual shelf links like '/shelf/show/{name}'.
    for a in soup.find_all("a", href=re.compile(r"/shelf/show/")):
        name_raw = a.get_text(strip=True)
        # Shelf count is usually in the next sibling span or in the same element
        count_node = a.find_next_sibling(string=re.compile(r"\d"))
        if count_node is None:
            # Try the parent element's text after the link
            parent_text = (a.parent or a).get_text(separator=" ")
            count_match = re.search(r"(\d[\d,]*)", parent_text.replace(name_raw, "", 1))
        else:
            count_match = re.search(r"(\d[\d,]*)", str(count_node))

        count = 0
        if count_match:
            count = int(count_match.group(1).replace(",", ""))

        if name_raw:
            results.append((name_raw, count))

    # Also check the "People who shelved this also shelved" section and the
    # "Other editions" shelf tags that appear in data attributes.
    for span in soup.find_all("span", class_=re.compile(r"shelfStat")):
        text = span.get_text(separator=" ", strip=True)
        m = re.match(r"(.+?)\s+(\d[\d,]*)\s+people", text, re.IGNORECASE)
        if m:
            results.append((m.group(1).strip(), int(m.group(2).replace(",", ""))))

    # Deduplicate (keep max count per name)
    seen: dict[str, int] = {}
    for name, count in results:
        seen[name] = max(seen.get(name, 0), count)

    sorted_results = sorted(seen.items(), key=lambda x: x[1], reverse=True)
    return sorted_results[:MAX_SHELVES_PER_BOOK]


def _parse_reviews(html: str) -> list[str]:
    """
    Extract up to MAX_REVIEWS_PER_BOOK review texts from a Goodreads book page.
    Reviews are in elements with class 'reviewText' or similar.
    """
    soup = BeautifulSoup(html, "html.parser")
    reviews: list[str] = []

    # Primary: reviewText > span[id^='freeText']
    for span in soup.find_all("span", id=re.compile(r"^freeText")):
        text = span.get_text(separator=" ", strip=True)
        if text and len(text) > 50:   # skip very short snippets
            reviews.append(text)
        if len(reviews) >= MAX_REVIEWS_PER_BOOK:
            break

    # Fallback: reviewText containers
    if not reviews:
        for div in soup.find_all(class_="reviewText"):
            text = div.get_text(separator=" ", strip=True)
            if text and len(text) > 50:
                reviews.append(text)
            if len(reviews) >= MAX_REVIEWS_PER_BOOK:
                break

    return reviews


# ---------------------------------------------------------------------------
# Weight calculation
# ---------------------------------------------------------------------------

def _shelf_weight(shelf_count: int, total_shelved: int) -> float:
    """
    Convert absolute shelf count to a [0, 1] trope weight.

    shelf_proportion = shelf_count / total_shelved
    weight = min(1.0, shelf_proportion * 5)   (scale so 20% of shelves → 1.0)
    """
    if total_shelved <= 0:
        return 0.0
    proportion = shelf_count / total_shelved
    return min(1.0, proportion * 5.0)


# ---------------------------------------------------------------------------
# DB write helpers
# ---------------------------------------------------------------------------

async def _get_trope_id_by_name(db, name: str) -> Optional[int]:
    """Return the trope_id for the given canonical trope name, or None."""
    row = await db.execute(select(Trope.trope_id).where(Trope.name == name))
    result = row.scalar_one_or_none()
    return result


async def _write_tropes(
    db,
    book_id: int,
    shelves: list[tuple[str, int]],
    *,
    dry_run: bool = False,
) -> int:
    """
    Map shelves to canonical tropes and upsert into book_tropes.
    Returns the number of tropes written.
    """
    total_shelved = sum(c for _, c in shelves)
    written = 0

    for shelf_name, shelf_count in shelves:
        if shelf_count < MIN_SHELF_COUNT:
            continue
        proportion = shelf_count / total_shelved if total_shelved > 0 else 0
        if proportion < MIN_SHELF_PROPORTION:
            continue

        # Normalise: lowercase + strip
        key = shelf_name.lower().strip()
        canonical = SHELF_TO_TROPE.get(key)
        if canonical is None:
            # Try replacing hyphens with spaces
            canonical = SHELF_TO_TROPE.get(key.replace("-", " "))
        if canonical is None:
            continue

        trope_id = await _get_trope_id_by_name(db, canonical)
        if trope_id is None:
            logger.debug("Canonical trope '%s' not found in DB — skipping", canonical)
            continue

        weight = _shelf_weight(shelf_count, total_shelved)

        if dry_run:
            logger.info("  [dry-run] would write trope '%s' (weight=%.3f) for book %d",
                        canonical, weight, book_id)
            written += 1
            continue

        # Check if an admin-set tag already exists for this pair
        existing = await db.execute(
            select(BookTrope).where(
                BookTrope.book_id == book_id,
                BookTrope.trope_id == trope_id,
            )
        )
        existing_row: Optional[BookTrope] = existing.scalar_one_or_none()

        if existing_row is not None:
            if not existing_row.is_crowd_promoted:
                # Admin tag — never overwrite
                logger.debug("  Admin tag '%s' on book %d — skipping crowd write", canonical, book_id)
                continue
            # Update existing crowd-promoted row
            existing_row.weight = weight
        else:
            db.add(BookTrope(
                book_id=book_id,
                trope_id=trope_id,
                weight=weight,
                is_crowd_promoted=True,
            ))

        written += 1

    if not dry_run and written > 0:
        await db.commit()

    return written


async def _write_review_embedding(db, book_id: int, reviews: list[str]) -> None:
    """Embed the concatenated scraped review texts and write to books.review_embedding."""
    if not reviews:
        return

    combined = " | ".join(reviews)
    if not combined.strip():
        return

    # Use the same description model and async helper as the rest of the pipeline.
    from app.services.embedding import _get_description_model, _run  # noqa: PLC0415

    embedding = await _run(combined, _get_description_model)

    await db.execute(
        update(Book)
        .where(Book.book_id == book_id)
        .values(review_embedding=embedding)
    )
    await db.commit()
    logger.debug("  Wrote review_embedding for book %d", book_id)


async def _trigger_genome_embed_if_ready(db, book_id: int) -> bool:
    """
    Check canonical trope count. If ≥ TROPE_THRESHOLD and book has no
    genome_embedding yet, trigger an embed. Returns True if embed was triggered.
    """
    count_row = await db.execute(
        select(func.count()).where(BookTrope.book_id == book_id)
    )
    trope_count = count_row.scalar_one()

    if trope_count < TROPE_THRESHOLD:
        return False

    book = await db.get(Book, book_id)
    if book is None or book.genome_embedding is not None:
        return False

    logger.info("  Triggering genome embed for book %d (trope count = %d)", book_id, trope_count)
    await embed_book(book_id, db)
    return True


# ---------------------------------------------------------------------------
# Per-book enrichment
# ---------------------------------------------------------------------------

async def enrich_book(
    client: httpx.AsyncClient,
    book: Book,
    *,
    dry_run: bool = False,
) -> dict:
    """
    Enrich a single book from Goodreads. Returns a result dict with keys:
      found, tropes_written, reviews_found, genome_triggered, error
    """
    result: dict = {
        "book_id": book.book_id,
        "isbn": book.isbn,
        "found": False,
        "tropes_written": 0,
        "reviews_found": 0,
        "genome_triggered": False,
        "error": None,
    }

    isbn = book.isbn
    if not isbn:
        result["error"] = "no_isbn"
        return result

    # --- Step 1: Search for book page ---
    search_url = GOODREADS_SEARCH.format(isbn=isbn)
    search_html = await _get_html(client, search_url)
    if search_html is None:
        result["error"] = "search_failed"
        return result

    book_path = _find_book_path(search_html)
    if book_path is None:
        logger.debug("Book %d (%s) not found on Goodreads", book.book_id, isbn)
        result["error"] = "not_found"
        return result

    result["found"] = True
    book_url = GOODREADS_BOOK.format(path=book_path)

    # Small delay before hitting book page
    await asyncio.sleep(random.uniform(0.3, 0.7))

    # --- Step 2: Fetch book page ---
    book_html = await _get_html(client, book_url)
    if book_html is None:
        result["error"] = "book_page_failed"
        return result

    # --- Step 3: Parse shelves and reviews ---
    shelves = _parse_shelves(book_html)
    reviews = _parse_reviews(book_html)
    result["reviews_found"] = len(reviews)

    logger.info(
        "Book %d '%s' — found on Goodreads, %d shelves, %d reviews",
        book.book_id, book.title, len(shelves), len(reviews),
    )

    # --- Step 4: Write to DB ---
    async with AsyncSessionLocal() as db:
        # Write tropes
        tropes_written = await _write_tropes(db, book.book_id, shelves, dry_run=dry_run)
        result["tropes_written"] = tropes_written

        # Write review embedding
        if not dry_run and reviews:
            await _write_review_embedding(db, book.book_id, reviews)

        # Trigger genome embed if threshold reached
        if not dry_run and tropes_written > 0:
            genome_triggered = await _trigger_genome_embed_if_ready(db, book.book_id)
            result["genome_triggered"] = genome_triggered

    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def run(
    *,
    limit: Optional[int],
    dry_run: bool,
    single_isbn: Optional[str],
    only_without_genome: bool,
) -> None:
    async with AsyncSessionLocal() as db:
        q = select(Book).where(Book.isbn.is_not(None))

        if only_without_genome:
            q = q.where(Book.genome_embedding.is_(None))

        if single_isbn:
            q = q.where((Book.isbn == single_isbn) | (Book.isbn13 == single_isbn))

        if limit:
            q = q.limit(limit)

        result = await db.execute(q)
        books: list[Book] = list(result.scalars().all())

    logger.info(
        "Enriching %d books (dry_run=%s, only_without_genome=%s)",
        len(books), dry_run, only_without_genome,
    )

    stats = {
        "total": len(books),
        "found": 0,
        "tropes_written": 0,
        "reviews_embedded": 0,
        "genome_triggered": 0,
        "errors": 0,
    }

    async with httpx.AsyncClient(
        timeout=30.0,
        headers=_HEADERS,
        follow_redirects=True,
    ) as client:
        for i, book in enumerate(books, 1):
            logger.info("[%d/%d] %s (id=%d, isbn=%s)",
                        i, len(books), book.title, book.book_id, book.isbn)
            try:
                res = await enrich_book(client, book, dry_run=dry_run)
            except Exception as exc:
                logger.exception("Unexpected error enriching book %d: %s", book.book_id, exc)
                stats["errors"] += 1
                continue

            if res["found"]:
                stats["found"] += 1
            if res.get("error"):
                stats["errors"] += 1
            stats["tropes_written"] += res["tropes_written"]
            if res["reviews_found"] > 0:
                stats["reviews_embedded"] += 1
            if res["genome_triggered"]:
                stats["genome_triggered"] += 1

            # Rate-limit between books
            delay = BASE_DELAY_S + random.uniform(0, JITTER_MAX_S)
            await asyncio.sleep(delay)

    logger.info(
        "\n=== Enrichment complete ===\n"
        "  Books targeted    : %d\n"
        "  Found on GR       : %d\n"
        "  Tropes written    : %d\n"
        "  Reviews embedded  : %d\n"
        "  Genome triggered  : %d\n"
        "  Errors            : %d",
        stats["total"],
        stats["found"],
        stats["tropes_written"],
        stats["reviews_embedded"],
        stats["genome_triggered"],
        stats["errors"],
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Enrich CommonThread books with Goodreads shelf + review data."
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Maximum number of books to enrich (default: all)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print what would be written without modifying the database",
    )
    parser.add_argument(
        "--isbn", type=str, default=None,
        help="Enrich a single book by ISBN (ISBN-10 or ISBN-13)",
    )
    parser.add_argument(
        "--all", dest="all_books", action="store_true",
        help="Enrich all books (including those with existing genome embeddings)",
    )
    args = parser.parse_args()

    asyncio.run(run(
        limit=args.limit,
        dry_run=args.dry_run,
        single_isbn=args.isbn,
        only_without_genome=not args.all_books,
    ))


if __name__ == "__main__":
    main()
