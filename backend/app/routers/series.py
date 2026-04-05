from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.database import get_db
from app.schemas.series import SeriesCreate, SeriesRead

router = APIRouter(prefix="/series", tags=["series"])


@router.get("/", response_model=list[SeriesRead])
async def list_series(db: AsyncSession = Depends(get_db)):
    return await crud.series.list_series(db)


@router.get("/{series_id}", response_model=SeriesRead)
async def get_series(series_id: int, db: AsyncSession = Depends(get_db)):
    series = await crud.series.get_by_id(db, series_id)
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")
    return series


@router.post("/", response_model=SeriesRead, status_code=201)
async def create_series(data: SeriesCreate, db: AsyncSession = Depends(get_db)):
    existing = await crud.series.get_by_name(db, data.name)
    if existing:
        raise HTTPException(status_code=409, detail="Series with this name already exists")
    return await crud.series.create_series(db, data)


@router.put("/{series_id}", response_model=SeriesRead)
async def update_series(
    series_id: int, data: SeriesCreate, db: AsyncSession = Depends(get_db)
):
    series = await crud.series.get_by_id(db, series_id)
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")
    return await crud.series.update_series(db, series, data)


@router.delete("/{series_id}", status_code=204)
async def delete_series(series_id: int, db: AsyncSession = Depends(get_db)):
    series = await crud.series.get_by_id(db, series_id)
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")
    await crud.series.delete_series(db, series)
