"""
Open Library API scraper.

Flow
----
1. OpenLibraryScraper.scrape_subject(subject, limit, progress, output_path)
     → paginates GET /search.json?subject={subject}&limit=100&page=N
     → for each work, fetches description from GET /works/{id}.json
     → deduplicates by ol_work_key
     → appends ScrapedBook as JSONL to output_path

API endpoints used
------------------
Search:      https://openlibrary.org/search.json
Works:       https://openlibrary.org/works/{id}.json
Covers:      https://covers.openlibrary.org/b/id/{cover_id}-L.jpg

Rate limiting
-------------
Open Library asks for reasonable use. We use a semaphore to cap concurrent
requests at CONCURRENCY (default 5) and add a small inter-request delay.
No Playwright / browser required — pure async HTTP.

Usage
-----
    scraper = OpenLibraryScraper(delay_ms=200, concurrency=5)
    async with scraper:
        await scraper.scrape_subject("fantasy", limit=250, ...)
"""

from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path
from typing import Any, Optional

import httpx

from .models import ScrapedBook, ScrapeProgress

logger = logging.getLogger(__name__)

SEARCH_URL = "https://openlibrary.org/search.json"
WORKS_URL  = "https://openlibrary.org/works/{work_id}.json"
COVER_URL  = "https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"

PAGE_SIZE   = 100   # Open Library max results per search page
MAX_RETRIES = 3
RETRY_BASE  = 1.0   # seconds; doubles each retry


class OpenLibraryScraper:
    """
    Async Open Library API scraper.

    Parameters
    ----------
    delay_ms:
        Delay between consecutive description fetches (ms).
        Search pages are fetched sequentially; description fetches run
        concurrently up to `concurrency`.
    concurrency:
        Max simultaneous description-fetch requests.
    """

    def __init__(self, delay_ms: int = 200, concurrency: int = 5) -> None:
        self.delay_ms = delay_ms
        self.concurrency = concurrency
        self._client: Optional[httpx.AsyncClient] = None
        self._sem: Optional[asyncio.Semaphore] = None

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "OpenLibraryScraper":
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers={"User-Agent": "CommonThread/1.0 (educational project; pyang4071@edu)"},
            follow_redirects=True,
        )
        self._sem = asyncio.Semaphore(self.concurrency)
        return self

    async def __aexit__(self, *_) -> None:
        if self._client:
            await self._client.aclose()

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    async def _get(self, url: str, params: Optional[dict] = None) -> Optional[dict]:
        """GET JSON with retry on transient errors. Returns None on failure."""
        assert self._client is not None, "Scraper not started — use async with"
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = await self._client.get(url, params=params)
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    return None  # not found — don't retry
                logger.warning("HTTP %s on %s (attempt %d/%d)",
                               exc.response.status_code, url, attempt, MAX_RETRIES)
            except (httpx.TransportError, httpx.TimeoutException) as exc:
                logger.warning("Transport error on %s: %s (attempt %d/%d)",
                               url, exc, attempt, MAX_RETRIES)
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_BASE * (2 ** (attempt - 1)))
        logger.error("All retries exhausted for %s", url)
        return None

    # ------------------------------------------------------------------
    # Description fetch
    # ------------------------------------------------------------------

    async def _get_description(self, work_key: str) -> Optional[str]:
        """
        Fetch description from /works/{id}.json.
        The description field may be a plain string or
        {"type": "/type/text", "value": "..."}.
        """
        work_id = work_key.lstrip("/").split("/")[-1]   # "/works/OL45804W" → "OL45804W"
        async with self._sem:
            data = await self._get(WORKS_URL.format(work_id=work_id))
            if not data:
                return None
            raw = data.get("description")
            if isinstance(raw, str):
                return raw.strip() or None
            if isinstance(raw, dict):
                return (raw.get("value") or "").strip() or None
            return None

    # ------------------------------------------------------------------
    # Search page fetch
    # ------------------------------------------------------------------

    async def _search_page(self, subject: str, page: int) -> Optional[dict]:
        """Fetch one page of search results for a subject."""
        params = {
            "subject": subject,
            "limit": PAGE_SIZE,
            "page": page,
            "fields": (
                "key,title,author_name,isbn,subject,"
                "first_publish_year,publisher,number_of_pages_median,"
                "cover_i,language,edition_count"
            ),
        }
        return await self._get(SEARCH_URL, params=params)

    # ------------------------------------------------------------------
    # Parse a single search doc into a ScrapedBook
    # ------------------------------------------------------------------

    def _parse_doc(self, doc: dict[str, Any], subject: str) -> Optional[ScrapedBook]:
        """Convert a raw search result doc to a ScrapedBook. Returns None if unusable."""
        work_key: str = doc.get("key", "")
        if not work_key:
            return None

        title: str = (doc.get("title") or "").strip()
        if not title:
            return None

        authors: list[str] = doc.get("author_name") or []

        # ISBNs — Open Library returns a flat list mixing 10 and 13 digit
        raw_isbns: list[str] = doc.get("isbn") or []
        isbn10 = next((i for i in raw_isbns if len(re.sub(r"[^0-9X]", "", i)) == 10), None)
        isbn13 = next((i for i in raw_isbns if len(re.sub(r"[^0-9X]", "", i)) == 13), None)

        subjects: list[str] = doc.get("subject") or []

        # First publisher from the list
        publishers: list[str] = doc.get("publisher") or []
        publisher = publishers[0] if publishers else None

        # Language — Open Library codes like ["eng", "fre"]
        langs: list[str] = doc.get("language") or []
        language = langs[0] if langs else None

        cover_id: Optional[int] = doc.get("cover_i")
        cover_url = COVER_URL.format(cover_id=cover_id) if cover_id else None

        return ScrapedBook(
            ol_work_key=work_key,
            ol_cover_id=cover_id,
            title=title,
            authors=authors,
            isbn=isbn10,
            isbn13=isbn13,
            publication_year=doc.get("first_publish_year"),
            publisher=publisher,
            page_count=doc.get("number_of_pages_median"),
            language=language,
            subjects=subjects[:30],   # cap at 30 to keep JSON compact
            cover_url=cover_url,
            discovered_via_subject=subject,
            edition_count=doc.get("edition_count"),
        )

    # ------------------------------------------------------------------
    # Main subject scrape
    # ------------------------------------------------------------------

    async def scrape_subject(
        self,
        subject: str,
        limit: int,
        progress: ScrapeProgress,
        output_path: Path,
    ) -> int:
        """
        Collect up to `limit` books for `subject` and append to output_path as JSONL.
        Updates `progress` in-place. Returns number of new books written.
        """
        already_keys: set[str] = set(progress.in_progress.get(subject, []))
        logger.info("[%s] starting (already have %d)", subject, len(already_keys))

        collected: list[ScrapedBook] = []
        seen_keys: set[str] = set(already_keys)
        page = 1

        # ---- Phase 1: collect works from search pages ----
        while len(collected) < limit:
            logger.info("  [%s] search page %d (collected %d/%d)",
                        subject, page, len(collected), limit)

            data = await self._search_page(subject, page)
            if not data:
                logger.error("  [%s] failed to fetch search page %d", subject, page)
                break

            docs: list[dict] = data.get("docs") or []
            if not docs:
                logger.info("  [%s] no more results at page %d", subject, page)
                break

            new_this_page = 0
            for doc in docs:
                book = self._parse_doc(doc, subject)
                if book is None or book.ol_work_key in seen_keys:
                    continue
                seen_keys.add(book.ol_work_key)
                collected.append(book)
                new_this_page += 1
                if len(collected) >= limit:
                    break

            if new_this_page == 0:
                logger.info("  [%s] no new works on page %d — stopping", subject, page)
                break

            page += 1
            # Small delay between search pages
            await asyncio.sleep(self.delay_ms / 1000)

        logger.info("  [%s] collected %d works; fetching descriptions …", subject, len(collected))

        # ---- Phase 2: fetch descriptions concurrently ----
        async def fetch_desc(book: ScrapedBook) -> ScrapedBook:
            desc = await self._get_description(book.ol_work_key)
            await asyncio.sleep(self.delay_ms / 1000)
            return book.model_copy(update={"description": desc})

        books_with_desc = await asyncio.gather(*[fetch_desc(b) for b in collected])

        # ---- Phase 3: write to JSONL ----
        written = 0
        with output_path.open("a", encoding="utf-8") as fh:
            for book in books_with_desc:
                fh.write(book.model_dump_json() + "\n")
                progress.in_progress.setdefault(subject, []).append(book.ol_work_key)
                progress.total_books_scraped += 1
                written += 1

        logger.info("[%s] done — wrote %d books", subject, written)
        return written
