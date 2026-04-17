import asyncio

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.crud import rating as crud_rating
from app.database import get_db
from app.database.engine import AsyncSessionLocal
from app.models.user import AppUser
from app.schemas.rating import RatingRead, RatingUpsert, ReviewRead
from app.services.embedding import embed_reviews_for_book

router = APIRouter(prefix="/books", tags=["ratings"])
ratings_router = APIRouter(prefix="/ratings", tags=["ratings"])


@router.get("/{book_id}/rating", response_model=RatingRead | None)
async def get_my_rating(
    book_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    return await crud_rating.get_rating(db, current_user.user_id, book_id)


async def _embed_reviews_in_background(book_id: int) -> None:
    async with AsyncSessionLocal() as db:
        try:
            await embed_reviews_for_book(book_id, db)
        except Exception:
            pass  # review embedding is best-effort; never fail a rating save


@router.put("/{book_id}/rating", response_model=RatingRead)
async def upsert_rating(
    book_id: int,
    data: RatingUpsert,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    rating = await crud_rating.upsert_rating(
        db, current_user.user_id, book_id, data.rating, data.review_text
    )
    if data.review_text:
        asyncio.create_task(_embed_reviews_in_background(book_id))
    return rating


@router.delete("/{book_id}/rating", status_code=204)
async def delete_rating(
    book_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    removed = await crud_rating.delete_rating(db, current_user.user_id, book_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Rating not found")


@router.get("/{book_id}/reviews", response_model=list[ReviewRead])
async def get_book_reviews(
    book_id: int,
    db: AsyncSession = Depends(get_db),
):
    ratings = await crud_rating.get_book_reviews(db, book_id)
    return [
        ReviewRead(
            rating_id=r.rating_id,
            book_id=r.book_id,
            rating=r.rating,
            review_text=r.review_text,  # type: ignore[arg-type]  # filtered by is_not(None)
            reviewer_name=r.user.name if r.user else None,
            created_at=r.created_at,
        )
        for r in ratings
    ]


@ratings_router.get("/my", response_model=list[RatingRead])
async def get_my_ratings(
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    return await crud_rating.list_my_ratings(db, current_user.user_id)
