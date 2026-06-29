from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import uuid

from app.db.models.pattern import DetectedPattern, PatternCategory
from app.repositories.base import BaseRepository


class PatternRepository(BaseRepository[DetectedPattern]):

    def __init__(self, db: AsyncSession):
        super().__init__(db, DetectedPattern)

    async def bulk_create(
        self, patterns: list[DetectedPattern]
    ) -> list[DetectedPattern]:
        """
        Insert multiple patterns in one operation.

        Why bulk insert instead of calling create() in a loop?
        A loop with 10 patterns fires 10 separate INSERT statements.
        Bulk insert fires one statement with 10 rows.
        At scale (1000 patterns), this is the difference between
        1000 round trips and 1 round trip to the database.
        """
        for pattern in patterns:
            self.db.add(pattern)
        await self.db.flush()
        return patterns

    async def get_pattern_distribution(
        self, user_id: uuid.UUID
    ) -> list[dict]:
        """
        Pattern frequency across all of a user's scans.
        Used in the analytics dashboard pie chart.
        """
        result = await self.db.execute(
            select(
                DetectedPattern.category,
                func.count(DetectedPattern.id).label("count"),
            )
            .join(DetectedPattern.scan)
            .where(DetectedPattern.scan.has(user_id=user_id))
            .group_by(DetectedPattern.category)
            .order_by(func.count(DetectedPattern.id).desc())
        )
        return [
            {"category": row.category.value, "count": row.count}
            for row in result.all()
        ]