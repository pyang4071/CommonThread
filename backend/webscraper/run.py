"""
CLI entry point for the Open Library book scraper.

Usage examples
--------------
# Scrape all built-in subjects, 250 books each:
    uv run python -m webscraper.run

# Scrape only Fantasy and Mystery, 100 books each:
    uv run python -m webscraper.run --subjects fantasy mystery --books-per-subject 100

# Resume a previous run:
    uv run python -m webscraper.run --resume

Output
------
Each run writes to --output-dir (default: webscraper/output/).

  output/
    books_<subject>.jsonl   ← one JSON object per line per subject
    progress.json           ← checkpoint (resume state)
    summary.json            ← written on completion
    scrape.log              ← full log
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from .models import ScrapeProgress
from .scraper import OpenLibraryScraper

# ---------------------------------------------------------------------------
# Built-in subject list
# These map directly to Open Library subject search terms.
# ---------------------------------------------------------------------------

DEFAULT_SUBJECTS = [
    "fantasy",
    "mystery",
    "romance",
    "science fiction",
    "thriller",
    "historical fiction",
    "horror",
    "young adult",
    "biography",
    "self-help",
    "classics",
    "literary fiction",
    "adventure",
    "crime",
    "philosophy",
    "psychology",
    "humor",
    "poetry",
    "graphic novels",
    "short stories",
]


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def _setup_logging(output_dir: Path) -> None:
    log_path = output_dir / "scrape.log"
    fmt = "%(asctime)s  %(levelname)-8s  %(name)s — %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=fmt,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_path, encoding="utf-8"),
        ],
    )


# ---------------------------------------------------------------------------
# Progress persistence
# ---------------------------------------------------------------------------

PROGRESS_FILE = "progress.json"


def _load_progress(output_dir: Path) -> ScrapeProgress:
    p = output_dir / PROGRESS_FILE
    if p.exists():
        try:
            return ScrapeProgress.model_validate_json(p.read_text(encoding="utf-8"))
        except Exception as exc:
            logging.warning("Could not load progress file: %s — starting fresh", exc)
    return ScrapeProgress()


def _save_progress(progress: ScrapeProgress, output_dir: Path) -> None:
    p = output_dir / PROGRESS_FILE
    p.write_text(progress.model_dump_json(indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Main async logic
# ---------------------------------------------------------------------------

async def run(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    _setup_logging(output_dir)
    logger = logging.getLogger("run")

    subjects: list[str] = args.subjects if args.subjects else DEFAULT_SUBJECTS

    logger.info("=" * 60)
    logger.info("CommonThread Open Library scraper — %s",
                datetime.now(timezone.utc).isoformat())
    logger.info("Output dir  : %s", output_dir.resolve())
    logger.info("Target      : %d books per subject", args.books_per_subject)
    logger.info("Delay       : %d ms", args.delay_ms)
    logger.info("Concurrency : %d", args.concurrency)
    logger.info("")
    logger.info("Subjects (%d total):", len(subjects))
    for i, s in enumerate(subjects, 1):
        logger.info("  %3d. %s", i, s)
    logger.info("=" * 60)

    progress = _load_progress(output_dir) if args.resume else ScrapeProgress()
    _save_progress(progress, output_dir)

    remaining = [s for s in subjects if s not in progress.completed_subjects]
    logger.info("%d subjects to scrape (%d already completed)",
                len(remaining), len(progress.completed_subjects))

    async with OpenLibraryScraper(
        delay_ms=args.delay_ms,
        concurrency=args.concurrency,
    ) as scraper:
        for i, subject in enumerate(remaining, 1):
            out_file = output_dir / f"books_{subject.replace(' ', '_')}.jsonl"

            logger.info("")
            logger.info("── Subject %d/%d: %s ──", i, len(remaining), subject)

            try:
                written = await scraper.scrape_subject(
                    subject=subject,
                    limit=args.books_per_subject,
                    progress=progress,
                    output_path=out_file,
                )
                logger.info("Subject '%s' complete — %d books → %s",
                            subject, written, out_file.name)
                progress.completed_subjects.append(subject)
                progress.in_progress.pop(subject, None)

            except KeyboardInterrupt:
                logger.warning("Interrupted — saving progress and exiting")
                _save_progress(progress, output_dir)
                sys.exit(0)

            except Exception as exc:
                logger.error("Error scraping '%s': %s", subject, exc, exc_info=True)

            finally:
                _save_progress(progress, output_dir)

    logger.info("")
    logger.info("=" * 60)
    logger.info("Scrape complete.")
    logger.info("Total books written: %d", progress.total_books_scraped)
    logger.info("Completed subjects : %d", len(progress.completed_subjects))

    summary = {
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "total_books": progress.total_books_scraped,
        "completed_subjects": progress.completed_subjects,
        "books_per_subject_target": args.books_per_subject,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    logger.info("Summary → %s", output_dir / "summary.json")
    logger.info("=" * 60)


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m webscraper.run",
        description="Fetch book metadata from Open Library and save to JSONL files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--subjects",
        nargs="+",
        metavar="SUBJECT",
        default=None,
        help=(
            "Space-separated list of subjects to scrape "
            "(e.g. fantasy romance mystery). "
            "Defaults to the built-in list of 20 subjects."
        ),
    )
    parser.add_argument(
        "--books-per-subject",
        type=int,
        default=500,
        metavar="N",
        help="Target number of books per subject (default: 500).",
    )
    parser.add_argument(
        "--output-dir",
        default="webscraper/output",
        metavar="DIR",
        help="Directory for JSONL files and logs (default: webscraper/output).",
    )
    parser.add_argument(
        "--delay-ms",
        type=int,
        default=200,
        metavar="MS",
        help="Delay between API requests in ms (default: 200).",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        metavar="N",
        help="Max concurrent description-fetch requests (default: 5).",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        default=False,
        help="Resume from a previous run using progress.json in --output-dir.",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    args = _parse_args()
    asyncio.run(run(args))
