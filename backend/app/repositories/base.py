from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from typing import TypeVar, Generic, Type
import uuid

from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Generic repository implementing standard CRUD operations.

    Why Generic[ModelType]? This base class works for ANY model.
    UserRepository(BaseRepository[User]) gets all these methods
    pre-built for User, without duplicating code.

    This is the Repository Pattern:
    - Service layer never writes SQL
    - Repository layer never contains business logic
    - Clean separation = easy to test, easy to swap databases

    Interview talking point: "I used the repository pattern to
    decouple business logic from database access. To test a service,
    I mock the repository — the test never touches a real database."
    """

    def __init__(self, db: AsyncSession, model: Type[ModelType]):
        self.db = db
        self.model = model

    async def get_by_id(self, id: uuid.UUID) -> ModelType | None:
        result = await self.db.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ModelType]:
        result = await self.db.execute(
            select(self.model).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, obj: ModelType) -> ModelType:
        self.db.add(obj)
        await self.db.flush()   # Write to DB but don't commit yet
        await self.db.refresh(obj)  # Load DB-generated values (created_at etc.)
        return obj

    async def update(self, obj: ModelType) -> ModelType:
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete(self, id: uuid.UUID) -> bool:
        result = await self.db.execute(
            delete(self.model).where(self.model.id == id)
        )
        return result.rowcount > 0

    async def count(self) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(self.model)
        )
        return result.scalar_one()