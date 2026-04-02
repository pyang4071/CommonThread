from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.archetype import Archetype
from app.models.character_dna import CharacterDNA
from app.schemas.archetype import ArchetypeCreate, ArchetypeUpdate


async def get_archetype(db: AsyncSession, archetype_id: int) -> Archetype | None:
    return await db.get(Archetype, archetype_id)


async def list_archetypes(db: AsyncSession, skip: int = 0, limit: int = 20) -> list[Archetype]:
    result = await db.execute(select(Archetype).offset(skip).limit(limit))
    return list(result.scalars().all())


async def create_archetype(db: AsyncSession, data: ArchetypeCreate) -> Archetype:
    archetype = Archetype(**data.model_dump())
    db.add(archetype)
    await db.commit()
    await db.refresh(archetype)
    return archetype


async def update_archetype(
    db: AsyncSession, archetype: Archetype, data: ArchetypeUpdate
) -> Archetype:
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(archetype, field, value)
    await db.commit()
    await db.refresh(archetype)
    return archetype


async def get_affected_book_ids(db: AsyncSession, archetype_id: int) -> list[int]:
    result = await db.execute(
        select(CharacterDNA.book_id).where(CharacterDNA.archetype_id == archetype_id)
    )
    return list(result.scalars().all())


async def delete_archetype(db: AsyncSession, archetype: Archetype) -> None:
    await db.delete(archetype)
    await db.commit()
