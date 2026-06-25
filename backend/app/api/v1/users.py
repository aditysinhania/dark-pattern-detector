from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db
from app.schemas.user import UserResponse, UserUpdate, UserProfileResponse
from app.schemas.common import DataResponse
from app.services.auth import AuthService
from app.core.dependencies import get_current_active_user, require_admin
from app.db.models.user import User
from app.db.models.scan import Scan
from app.repositories.user import UserRepository

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=DataResponse[UserProfileResponse],
    summary="Get current user profile with stats",
)
async def get_my_profile(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[UserProfileResponse]:
    """
    Returns profile with aggregated scan statistics.
    Demonstrates how to join data without N+1 queries.
    """
    # Single query to get scan count and total patterns
    # Instead of: user.scans (loads all scans) then count in Python
    result = await db.execute(
        select(
            func.count(Scan.id).label("total_scans"),
            func.coalesce(func.sum(Scan.patterns_found), 0).label("total_patterns"),
        ).where(Scan.user_id == current_user.id)
    )
    stats = result.one()

    profile = UserProfileResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at,
        total_scans=stats.total_scans,
        total_patterns_found=stats.total_patterns,
    )

    return DataResponse(data=profile)


@router.patch(
    "/me",
    response_model=DataResponse[UserResponse],
    summary="Update current user profile",
)
async def update_my_profile(
    data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[UserResponse]:
    """
    PATCH semantics: only provided fields are updated.
    Sending {"full_name": "New Name"} only changes the name.
    """
    service = AuthService(db)
    updated_user = await service.update_profile(current_user, data)
    return DataResponse(
        message="Profile updated",
        data=UserResponse.model_validate(updated_user),
    )


@router.delete(
    "/me",
    response_model=DataResponse[dict],
    summary="Delete current user account",
)
async def delete_my_account(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[dict]:
    """
    Soft approach: deactivate rather than hard delete.

    Why not hard delete?
    - Referential integrity: scans reference users
    - Audit trail: you may need the data for legal reasons
    - Mistake recovery: user can contact support to restore

    Hard delete with CASCADE would work, but is irreversible.
    """
    user_repo = UserRepository(db)
    current_user.is_active = False
    await user_repo.update(current_user)
    return DataResponse(message="Account deactivated successfully", data={})


# ── Admin only routes ────────────────────────────────────────────────────────

@router.get(
    "/",
    response_model=DataResponse[list[UserResponse]],
    summary="List all users (admin only)",
)
async def list_users(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[list[UserResponse]]:
    """
    Admin endpoint to list all users.
    The require_admin dependency automatically returns 403
    for non-admin users — no manual check needed.
    """
    user_repo = UserRepository(db)
    users = await user_repo.get_all(skip=skip, limit=limit)
    return DataResponse(
        data=[UserResponse.model_validate(u) for u in users]
    )


@router.patch(
    "/{user_id}/deactivate",
    response_model=DataResponse[dict],
    summary="Deactivate a user account (admin only)",
)
async def deactivate_user(
    user_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[dict]:
    import uuid
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(uuid.UUID(user_id))

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account",
        )

    user.is_active = False
    await user_repo.update(user)
    return DataResponse(message=f"User {user.email} deactivated", data={})