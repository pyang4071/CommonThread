"""Every model table must have RLS enabled by some migration (via its RLS_TABLES list)."""
import importlib.util
from pathlib import Path

import app.models  # noqa: F401 — registers all models with Base.metadata
from app.database.base import Base

VERSIONS = Path(__file__).resolve().parents[1] / "migrations" / "versions"


def _rls_tables() -> set[str]:
    tables: set[str] = set()
    for path in VERSIONS.glob("*.py"):
        spec = importlib.util.spec_from_file_location(path.stem, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        tables.update(getattr(module, "RLS_TABLES", []))
    return tables


def test_every_model_table_has_rls():
    missing = set(Base.metadata.tables) - _rls_tables()
    assert not missing, (
        f"Tables without RLS: {sorted(missing)}. The migration that creates a table must run "
        "ALTER TABLE ... ENABLE ROW LEVEL SECURITY and list it in RLS_TABLES."
    )
