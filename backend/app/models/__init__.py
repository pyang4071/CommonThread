# Import all models here so Alembic autogenerate sees them via Base.metadata
from app.models.archetype import Archetype
from app.models.author import Author
from app.models.book import Book
from app.models.book_book_type import book_book_types  # noqa: F401
from app.models.book_genre import book_genres  # noqa: F401
from app.models.book_rating import BookRating
from app.models.book_trope import BookTrope
from app.models.book_type import BookType
from app.models.character_dna import CharacterDNA
from app.models.dislike import BookDislike
from app.models.genre import Genre
from app.models.series import Series
from app.models.tone import Tone
from app.models.trope import Trope
from app.models.user import AppUser
from app.models.user_book_archetype import UserBookArchetype
from app.models.user_book_trope import UserBookTrope
from app.models.user_follow import UserFollow

__all__ = [
    "Author", "Book", "Trope", "BookTrope", "Archetype", "CharacterDNA",
    "AppUser", "BookRating", "BookDislike", "Genre", "BookType", "Tone",
    "Series", "UserBookTrope", "UserBookArchetype", "UserFollow",
]
