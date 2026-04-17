"""
Pydantic models for scraped Open Library book data.

These are intermediate data structures used by the scraper before any
mapping into the CommonThread database schema.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ScrapedBook(BaseModel):
    """All raw data extracted from a single Open Library work."""

    # Open Library identifiers
    ol_work_key: str                    # e.g. "/works/OL45804W"
    ol_cover_id: Optional[int] = None  # integer used to build cover URL

    # Bibliographic metadata
    title: str
    authors: list[str] = Field(default_factory=list)
    isbn: Optional[str] = None          # ISBN-10 (first found)
    isbn13: Optional[str] = None        # ISBN-13 (first found, preferred)
    publication_year: Optional[int] = None
    publisher: Optional[str] = None

    # Content
    description: Optional[str] = None

    # Physical / format metadata
    page_count: Optional[int] = None
    language: Optional[str] = None

    # Classification (Open Library subjects — proxy for genre/tone)
    subjects: list[str] = Field(default_factory=list)

    # Cover URL (constructed from ol_cover_id)
    cover_url: Optional[str] = None

    # Which subject query this book was discovered under
    discovered_via_subject: Optional[str] = None

    # Edition count (rough popularity signal)
    edition_count: Optional[int] = None


class ScrapeProgress(BaseModel):
    """
    Checkpoint state persisted between runs as progress.json.
    Allows resuming without re-fetching already-visited subjects.
    """

    # Subjects fully scraped
    completed_subjects: list[str] = Field(default_factory=list)

    # Subjects in-progress: maps subject → list of already-scraped ol_work_keys
    in_progress: dict[str, list[str]] = Field(default_factory=dict)

    # Total books written so far
    total_books_scraped: int = 0
