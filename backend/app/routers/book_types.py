from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.auth import require_admin
from app.database import get_db
from app.models.user import AppUser
from app.schemas.book_type import BookTypeCreate, BookTypeRead, BookTypeUpdate

router = APIRouter(prefix="/book-types", tags=["book-types"])


@router.get("/", response_model=list[BookTypeRead])
async def list_book_types(db: AsyncSession = Depends(get_db)):
    return await crud.book_type.list_book_types(db)


@router.post("/", response_model=BookTypeRead, status_code=201)
async def create_book_type(data: BookTypeCreate, db: AsyncSession = Depends(get_db), _: AppUser = Depends(require_admin)):
    return await crud.book_type.create_book_type(db, data)


@router.get("/{book_type_id}", response_model=BookTypeRead)
async def get_book_type(book_type_id: int, db: AsyncSession = Depends(get_db)):
    bt = await crud.book_type.get_book_type(db, book_type_id)
    if not bt:
        raise HTTPException(status_code=404, detail="Book type not found")
    return bt


@router.put("/{book_type_id}", response_model=BookTypeRead)
async def update_book_type(book_type_id: int, data: BookTypeUpdate, db: AsyncSession = Depends(get_db), _: AppUser = Depends(require_admin)):
    bt = await crud.book_type.get_book_type(db, book_type_id)
    if not bt:
        raise HTTPException(status_code=404, detail="Book type not found")
    return await crud.book_type.update_book_type(db, bt, data)


@router.delete("/{book_type_id}", status_code=204)
async def delete_book_type(book_type_id: int, db: AsyncSession = Depends(get_db), _: AppUser = Depends(require_admin)):
    bt = await crud.book_type.get_book_type(db, book_type_id)
    if not bt:
        raise HTTPException(status_code=404, detail="Book type not found")
    await crud.book_type.delete_book_type(db, bt)
