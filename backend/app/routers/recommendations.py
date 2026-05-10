from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.auth import get_current_user
from app.database import get_db
from app.models.user import AppUser
from app.schemas.book import BookRead

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


class RecommendationExplanation(BaseModel):
    shared_tropes: list[str] = []
    shared_archetypes: list[str] = []
    source: str = "embedding"  # "embedding" | "collaborative"


class SimilarBook(BaseModel):
    book: BookRead
    score: float
    explanation: RecommendationExplanation | None = None


@router.get("/for-you", response_model=list[SimilarBook])
async def for_you(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    results = await crud.book.get_recommendations_for_user(db, current_user.user_id, limit=limit)
    return [
        SimilarBook(
            book=b,
            score=round(score, 4),
            explanation=RecommendationExplanation(**exp),
        )
        for b, score, exp in results
    ]


@router.get("/{book_id}/similar", response_model=list[SimilarBook])
async def similar_books(
    book_id: int,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    book = await crud.book.get_book(db, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    results = await crud.book.get_similar_books(db, book_id, limit=limit)
    return [
        SimilarBook(
            book=b,
            score=round(score, 4),
            explanation=RecommendationExplanation(**exp),
        )
        for b, score, exp in results
    ]
