from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.db.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """
    User-specific database operations.

    BaseRepository gives us get_by_id, get_all, create,
    update, delete for free. We only add what's unique to User.
    """

    def __init__(self, db: AsyncSession):
        super().__init__(db, User)

    async def get_by_email(self, email: str) -> User | None:
        """
        Used during login and registration to check if
        email exists. Indexed column = fast query.
        """
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_email_active(self, email: str) -> User | None:
        """
        Only returns active users. Used in authentication —
        disabled accounts should not be able to log in.
        """
        result = await self.db.execute(
            select(User).where(
                User.email == email,
                User.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    async def email_exists(self, email: str) -> bool:
        """
        Lightweight check — doesn't load the full User object.
        Used in registration to check for duplicates.
        """
        result = await self.db.execute(
            select(User.id).where(User.email == email)
        )
        return result.scalar_one_or_none() is not None