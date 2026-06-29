from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload
import uuid

from app.db.models.scan import Scan, ScanStatus
from app.db.models.pattern import DetectedPattern
from app.repositories.base import BaseRepository


class ScanRepository(BaseRepository[Scan]):
    """
    Scan-specific database operations.

    Key design decision: we use selectinload for relationships.
    This fires ONE additional query per relationship instead of
    a JOIN — much more predictable performance at scale.

    JOIN alternative: works great for small result sets,
    but with 1000 scans each having 10 patterns, a JOIN
    returns 10,000 rows. selectinload returns 1000 + 1000.
    """

    def __init__(self, db: AsyncSession):
        super().__init__(db, Scan)

    async def get_with_patterns(self, scan_id: uuid.UUID) -> Scan | None:
        """
        Load a scan with all its detected patterns in 2 queries.
        Used when returning full scan results to the client.
        """
        result = await self.db.execute(
            select(Scan)
            .options(selectinload(Scan.detected_patterns))
            .where(Scan.id == scan_id)
        )
        return result.scalar_one_or_none()

    async def get_user_scans(
        self,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Scan]:
        """
        Get paginated scans for a user, newest first.
        Pagination prevents loading thousands of scans at once.
        """
        result = await self.db.execute(
            select(Scan)
            .where(Scan.user_id == user_id)
            .order_by(desc(Scan.created_at))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_user_scan_count(self, user_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count(Scan.id)).where(Scan.user_id == user_id)
        )
        return result.scalar_one()

    async def update_status(
        self,
        scan_id: uuid.UUID,
        status: ScanStatus,
        **kwargs,
    ) -> None:
        """
        Update scan status and any additional fields atomically.
        Used by the Celery worker to report progress.
        """
        scan = await self.get_by_id(scan_id)
        if scan:
            scan.status = status
            for key, value in kwargs.items():
                setattr(scan, key, value)
            await self.db.flush()

    async def get_dashboard_stats(self, user_id: uuid.UUID) -> dict:
        """
        Single query for dashboard statistics.
        Aggregates in the database — never load all records to Python.
        """
        result = await self.db.execute(
            select(
                func.count(Scan.id).label("total_scans"),
                func.coalesce(
                    func.sum(Scan.patterns_found), 0
                ).label("total_patterns"),
                func.count(
                    Scan.id
                ).filter(Scan.status == ScanStatus.COMPLETED).label("completed"),
                func.count(
                    Scan.id
                ).filter(Scan.status == ScanStatus.FAILED).label("failed"),
            ).where(Scan.user_id == user_id)
        )
        row = result.one()
        return {
            "total_scans": row.total_scans,
            "total_patterns_found": row.total_patterns,
            "completed_scans": row.completed,
            "failed_scans": row.failed,
        }