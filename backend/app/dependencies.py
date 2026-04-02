from app.database.engine import get_db

# Re-export get_db as the canonical DB dependency.
# Future: add get_current_user here for Supabase JWT auth.
__all__ = ["get_db"]
