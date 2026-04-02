"""
Book cover fetching from OpenLibrary.

Strategy:
  1. If the book has an ISBN, probe the OpenLibrary Covers API directly.
     The URL always resolves — a 200 with a real image means a cover exists;
     a redirect to the 1×1 placeholder means it doesn't.
  2. If there's no ISBN (or the ISBN probe misses), fall back to the
     OpenLibrary Search API to find a cover_i and build the URL from that.
"""

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
) -> str | None:
    """
    Return a cover image URL for a book, or None if nothing is found.
    Tries ISBN first, then title+author search.
    """
    async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
        if isbn:
            url = await _probe_isbn(client, isbn)
            if url:
                return url

        return await _search_cover(client, title, author)


async def _probe_isbn(client: httpx.AsyncClient, isbn: str) -> str | None:
    """HEAD the ISBN cover URL — OpenLibrary returns 404 when no cover exists."""
    clean = isbn.replace("-", "").replace(" ", "")
    try:
        resp = await client.head(_OL_COVER_BY_ISBN.format(isbn=clean))
        if resp.status_code in (200, 302):
            return f"https://covers.openlibrary.org/b/isbn/{clean}-L.jpg"
    except httpx.HTTPError:
        logger.warning("Cover ISBN probe failed for ISBN %s", isbn)
    return None


async def _search_cover(client: httpx.AsyncClient, title: str, author: str) -> str | None:
    """Search OpenLibrary for the book and extract a cover_i if present."""
    try:
        resp = await client.get(
            _OL_SEARCH,
            params={"q": f"{title} {author}", "limit": 1, "fields": "cover_i"},
        )
        resp.raise_for_status()
        docs = resp.json().get("docs", [])
        if docs and docs[0].get("cover_i"):
            return _OL_COVER_BY_ID.format(cover_id=docs[0]["cover_i"])
    except httpx.HTTPError:
        logger.warning("Cover search failed for '%s' by %s", title, author)
    return None
