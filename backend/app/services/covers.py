"""
Book cover fetching from OpenLibrary.

Strategy:
  1. If the book has an ISBN, probe the OpenLibrary Covers API directly.
     The URL always resolves — a 200 with a real image means a cover exists;
     a redirect to the 1×1 placeholder means it doesn't.
  2. If there's no ISBN (or the ISBN probe misses), fall back to the
     OpenLibrary Search API to find a cover_i and build the URL from that.

Retries:
  Transient network/HTTP errors (timeouts, 5xx) are retried up to max_attempts
  times with exponential back-off (1 s, 2 s, …).  A clean "no cover found"
  (404 / empty search results) is not an error and is not retried.
"""

import asyncio
import logging

import httpx

logger = logging.getLogger(__name__)

_OL_COVER_BY_ISBN = "https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg?default=false"
_OL_COVER_BY_ID = "https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"
_OL_SEARCH = "https://openlibrary.org/search.json"


async def fetch_cover_url(
    isbn: str | None,
    title: str,
    author: str,
    max_attempts: int = 3,
) -> str | None:
    """
    Return a cover image URL for a book, or None if nothing is found.
    Tries ISBN first, then title+author search.
    Retries up to max_attempts times on transient network/HTTP errors.
    """
    for attempt in range(max_attempts):
        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
                if isbn:
                    url = await _probe_isbn(client, isbn)
                    if url:
                        return url
                return await _search_cover(client, title, author)
        except httpx.HTTPError as exc:
            logger.warning(
                "Cover fetch error (attempt %d/%d) for '%s': %s",
                attempt + 1, max_attempts, title, exc,
            )
            if attempt < max_attempts - 1:
                await asyncio.sleep(2 ** attempt)
    return None


async def _probe_isbn(client: httpx.AsyncClient, isbn: str) -> str | None:
    """HEAD the ISBN cover URL — OpenLibrary returns 404 when no cover exists."""
    clean = isbn.replace("-", "").replace(" ", "")
    resp = await client.head(_OL_COVER_BY_ISBN.format(isbn=clean))
    if resp.status_code in (200, 302):
        return f"https://covers.openlibrary.org/b/isbn/{clean}-L.jpg"
    return None


async def _search_cover(client: httpx.AsyncClient, title: str, author: str) -> str | None:
    """Search OpenLibrary for the book and extract a cover_i if present."""
    resp = await client.get(
        _OL_SEARCH,
        params={"q": f"{title} {author}", "limit": 1, "fields": "cover_i"},
    )
    resp.raise_for_status()
    docs = resp.json().get("docs", [])
    if docs and docs[0].get("cover_i"):
        return _OL_COVER_BY_ID.format(cover_id=docs[0]["cover_i"])
    return None
