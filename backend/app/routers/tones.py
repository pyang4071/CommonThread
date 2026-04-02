from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.auth import require_admin
from app.database import get_db
from app.models.user import AppUser
from app.schemas.tone import ToneCreate, ToneRead

router = APIRouter(prefix="/tones", tags=["tones"])


@router.get("/", response_model=list[ToneRead])
async def list_tones(db: AsyncSession = Depends(get_db)):
    return await crud.tone.list_tones(db)


@router.post("/", response_model=ToneRead, status_code=201)
async def create_tone(data: ToneCreate, db: AsyncSession = Depends(get_db), _: AppUser = Depends(require_admin)):
    return await crud.tone.create_tone(db, data)


@router.delete("/{tone_id}", status_code=204)
async def delete_tone(tone_id: int, db: AsyncSession = Depends(get_db), _: AppUser = Depends(require_admin)):
    tone = await crud.tone.get_tone(db, tone_id)
    if not tone:
        raise HTTPException(status_code=404, detail="Tone not found")
    await crud.tone.delete_tone(db, tone)
