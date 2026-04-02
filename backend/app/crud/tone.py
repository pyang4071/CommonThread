from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tone import Tone
from app.schemas.tone import ToneCreate


async def list_tones(db: AsyncSession) -> list[Tone]:
    result = await db.execute(select(Tone).order_by(Tone.name))
    return list(result.scalars().all())


async def get_tone(db: AsyncSession, tone_id: int) -> Tone | None:
    return await db.get(Tone, tone_id)


async def create_tone(db: AsyncSession, data: ToneCreate) -> Tone:
    tone = Tone(**data.model_dump())
    db.add(tone)
    await db.commit()
    await db.refresh(tone)
    return tone


async def delete_tone(db: AsyncSession, tone: Tone) -> None:
    await db.delete(tone)
    await db.commit()
