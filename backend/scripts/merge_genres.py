"""
Merge a duplicate genre into a canonical one and delete the duplicate.

Usage:
    cd backend
    uv run python scripts/merge_genres.py --from "Classics" --into "Classic"
"""

import argparse
import sys
import psycopg2
from app.config import settings


def merge(from_name: str, into_name: str, dry_run: bool = False) -> None:
    conn = psycopg2.connect(settings.SYNC_DATABASE_URL)
    conn.autocommit = False
    cur = conn.cursor()

    cur.execute("SELECT genre_id FROM genres WHERE name = %s", (into_name,))
    row = cur.fetchone()
    if not row:
        print(f"ERROR: canonical genre '{into_name}' not found.")
        conn.close()
        sys.exit(1)
    into_id = row[0]

    cur.execute("SELECT genre_id FROM genres WHERE name = %s", (from_name,))
    row = cur.fetchone()
    if not row:
        print(f"ERROR: source genre '{from_name}' not found.")
        conn.close()
        sys.exit(1)
    from_id = row[0]

    cur.execute("SELECT COUNT(*) FROM book_genres WHERE genre_id = %s", (from_id,))
    affected = cur.fetchone()[0]
    print(f"'{from_name}' (id={from_id}) → '{into_name}' (id={into_id})")
    print(f"Books to reassign: {affected}")

    if dry_run:
        print("Dry run — no changes made.")
        conn.close()
        return

    # Reassign books, skipping any that already have the canonical genre
    cur.execute("""
        UPDATE book_genres SET genre_id = %s
        WHERE genre_id = %s
          AND book_id NOT IN (
              SELECT book_id FROM book_genres WHERE genre_id = %s
          )
    """, (into_id, from_id, into_id))
    reassigned = cur.rowcount

    # Remove leftover rows (books that had both genres)
    cur.execute("DELETE FROM book_genres WHERE genre_id = %s", (from_id,))
    removed = cur.rowcount

    # Delete the duplicate genre
    cur.execute("DELETE FROM genres WHERE genre_id = %s", (from_id,))

    conn.commit()
    conn.close()
    print(f"Reassigned {reassigned} book(s), removed {removed} duplicate association(s), deleted genre '{from_name}'.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--from", dest="from_name", required=True, help="Genre to merge away (will be deleted)")
    parser.add_argument("--into", dest="into_name", required=True, help="Genre to keep")
    parser.add_argument("--dry-run", action="store_true", help="Preview without making changes")
    args = parser.parse_args()
    merge(args.from_name, args.into_name, dry_run=args.dry_run)
