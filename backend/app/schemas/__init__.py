from app.schemas.archetype import ArchetypeCreate, ArchetypeRead, ArchetypeUpdate
from app.schemas.book import (
    BookCreate,
    BookRead,
    BookReadDetail,
    BookTropeAttach,
    BookUpdate,
    CharacterDNAAttach,
)
from app.schemas.trope import TropeCreate, TropeRead, TropeUpdate

__all__ = [
    "BookCreate",
    "BookRead",
    "BookReadDetail",
    "BookTropeAttach",
    "BookUpdate",
    "CharacterDNAAttach",
    "TropeCreate",
    "TropeRead",
    "TropeUpdate",
    "ArchetypeCreate",
    "ArchetypeRead",
    "ArchetypeUpdate",
]
