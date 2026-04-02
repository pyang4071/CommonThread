from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.auth import require_admin
from app.database import get_db
from app.models.user import AppUser
from app.schemas.genre import GenreCreate, GenreRead, GenreUpdate

router = APIRouter(prefix="/genres", tags=["genres"])


@router.get("/", response_model=list[GenreRead])
async def list_genres(db: AsyncSession = Depends(get_db)):
    return await crud.genre.list_genres(db)


@router.post("/", response_model=GenreRead, status_code=201)
async def create_genre(data: GenreCreate, db: AsyncSession = Depends(get_db), _: AppUser = Depends(require_admin)):
    return await crud.genre.create_genre(db, data)


@router.get("/{genre_id}", response_model=GenreRead)
async def get_genre(genre_id: int, db: AsyncSession = Depends(get_db)):
    genre = await crud.genre.get_genre(db, genre_id)
    if not genre:
        raise HTTPException(status_code=404, detail="Genre not found")
    return genre


@router.put("/{genre_id}", response_model=GenreRead)
async def update_genre(genre_id: int, data: GenreUpdate, db: AsyncSession = Depends(get_db), _: AppUser = Depends(require_admin)):
    genre = await crud.genre.get_genre(db, genre_id)
    if not genre:
        raise HTTPException(status_code=404, detail="Genre not found")
    return await crud.genre.update_genre(db, genre, data)


@router.delete("/{genre_id}", status_code=204)
async def delete_genre(genre_id: int, db: AsyncSession = Depends(get_db), _: AppUser = Depends(require_admin)):
    genre = await crud.genre.get_genre(db, genre_id)
    if not genre:
        raise HTTPException(status_code=404, detail="Genre not found")
    await crud.genre.delete_genre(db, genre)
