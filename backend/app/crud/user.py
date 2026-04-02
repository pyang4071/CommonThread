import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import AppUser
from app.schemas.user import UserUpdate


async def get_by_id(db: AsyncSession, user_id: uuid.UUID) -> AppUser | None:
    return await db.get(AppUser, user_id)


async def get_by_email(db: AsyncSession, email: str) -> AppUser | None:
    result = await db.execute(select(AppUser).where(AppUser.email == email))
    return result.scalar_one_or_none()


async def get_or_create(
    db: AsyncSession, user_id: uuid.UUID, email: str, name: str | None = None
) -> AppUser:
    """Fetch existing profile or create one on first login."""
    user = await get_by_id(db, user_id)
    if not user:
        user = AppUser(user_id=user_id, email=email, name=name)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user


async def update(db: AsyncSession, user: AppUser, data: UserUpdate) -> AppUser:
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user)
    return user
