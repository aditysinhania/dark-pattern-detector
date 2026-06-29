from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.db.session import get_db
from app.schemas.scan import ScanRequest, ScanResponse, ScanDetailResponse
from app.schemas.common import DataResponse, PaginatedResponse
from app.core.dependencies import get_current_active_user
from app.db.models.user import User
from app.db.models.scan import Scan, ScanStatus
from app.repositories.scan import ScanRepository
from app.tasks.scan_tasks import run_scan_task
import math

router = APIRouter(prefix="/scans", tags=["Scans"])


@router.post(
    "/",
    response_model=DataResponse[ScanResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit a URL for dark pattern analysis",
)
async def create_scan(
    data: ScanRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ScanResponse]:
    """
    Submit a URL for scanning.

    Returns 202 Accepted immediately — the actual scan runs
    asynchronously via Celery. Poll GET /scans/{id} for results.

    Why 202 and not 200?
    HTTP 202 Accepted means "request received, processing has begun
    but is not complete." This is the correct semantic for async jobs.
    200 OK implies the operation completed synchronously.
    """
    scan_repo = ScanRepository(db)

    # Create scan record in PENDING state
    scan = Scan(
        user_id=current_user.id,
        url=data.url,
        status=ScanStatus.PENDING,
        patterns_found=0,
    )
    scan = await scan_repo.create(scan)
    await db.commit()

    # Queue Celery task
    task = run_scan_task.delay(
        scan_id=str(scan.id),
        url=data.url,
        user_id=str(current_user.id),
    )

    # Save task ID for status polling
    scan.task_id = task.id
    await scan_repo.update(scan)
    await db.commit()

    return DataResponse(
        message="Scan queued. Poll GET /scans/{id} for results.",
        data=ScanResponse.model_validate(scan),
    )


@router.get(
    "/{scan_id}",
    response_model=DataResponse[ScanDetailResponse],
    summary="Get scan status and results",
)
async def get_scan(
    scan_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ScanDetailResponse]:
    """
    Poll this endpoint after submitting a scan.
    Returns PENDING/PROCESSING until complete, then full results.
    """
    scan_repo = ScanRepository(db)
    scan = await scan_repo.get_with_patterns(scan_id)

    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan not found",
        )

    # Users can only see their own scans
    if scan.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    patterns = [
        {
            "id": str(p.id),
            "category": p.category.value,
            "detection_method": p.detection_method.value,
            "confidence_score": p.confidence_score,
            "explanation": p.explanation,
            "flagged_text": p.flagged_text,
            "suggestion": p.suggestion,
        }
        for p in scan.detected_patterns
    ]

    response_data = ScanDetailResponse(
        id=scan.id,
        url=scan.url,
        status=scan.status,
        risk_score=scan.risk_score,
        risk_level=scan.risk_level,
        patterns_found=scan.patterns_found,
        page_title=scan.page_title,
        screenshot_path=scan.screenshot_path,
        task_id=scan.task_id,
        error_message=scan.error_message,
        created_at=scan.created_at,
        detected_patterns=patterns,
    )

    return DataResponse(data=response_data)


@router.get(
    "/",
    response_model=PaginatedResponse[ScanResponse],
    summary="List user's scan history",
)
async def list_scans(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ScanResponse]:
    scan_repo = ScanRepository(db)
    skip = (page - 1) * page_size

    scans = await scan_repo.get_user_scans(
        current_user.id, skip=skip, limit=page_size
    )
    total = await scan_repo.get_user_scan_count(current_user.id)

    return PaginatedResponse(
        data=[ScanResponse.model_validate(s) for s in scans],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size),
    )


@router.get(
    "/dashboard/stats",
    response_model=DataResponse[dict],
    summary="Get dashboard statistics for current user",
)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[dict]:
    scan_repo = ScanRepository(db)
    stats = await scan_repo.get_dashboard_stats(current_user.id)
    return DataResponse(data=stats)