from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    RegisterResponse,
    ChangePasswordRequest,
)
from app.schemas.user import UserCreate, UserResponse
from app.schemas.common import DataResponse
from app.services.auth import AuthService
from app.core.security import create_access_token, create_refresh_token
from app.core.dependencies import get_current_active_user
from app.db.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=DataResponse[RegisterResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> DataResponse[RegisterResponse]:
    """
    Register a new user.

    - Validates email format and password strength
    - Returns JWT tokens immediately (no separate login needed)
    - Email verification happens separately (future phase)
    """
    service = AuthService(db)
    user = await service.register(data)

    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))

    return DataResponse(
        message="Account created successfully",
        data=RegisterResponse(
            user=UserResponse.model_validate(user),
            access_token=access_token,
            refresh_token=refresh_token,
        ),
    )


@router.post(
    "/login",
    response_model=DataResponse[TokenResponse],
    summary="Login and receive JWT tokens",
)
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> DataResponse[TokenResponse]:
    """
    Authenticate with email and password.
    Returns access token (30 min) and refresh token (7 days).
    """
    service = AuthService(db)
    user = await service.login(data.email, data.password)

    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))

    return DataResponse(
        message="Login successful",
        data=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserResponse.model_validate(user),
        ),
    )


@router.post(
    "/refresh",
    response_model=DataResponse[TokenResponse],
    summary="Refresh access token",
)
async def refresh_token(
    data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> DataResponse[TokenResponse]:
    """
    Exchange a refresh token for a new access + refresh token pair.
    The old refresh token is invalidated (token rotation).
    """
    service = AuthService(db)
    new_access, new_refresh = await service.refresh_access_token(data.refresh_token)

    # Decode to get user for response
    from app.core.security import decode_token
    from app.repositories.user import UserRepository
    import uuid

    payload = decode_token(new_access)
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(uuid.UUID(payload["sub"]))

    return DataResponse(
        message="Token refreshed",
        data=TokenResponse(
            access_token=new_access,
            refresh_token=new_refresh,
            user=UserResponse.model_validate(user),
        ),
    )


@router.post(
    "/change-password",
    response_model=DataResponse[dict],
    summary="Change current user password",
)
async def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[dict]:
    """
    Change password for the currently authenticated user.
    Requires current password for verification.
    """
    service = AuthService(db)
    await service.change_password(
        user=current_user,
        current_password=data.current_password,
        new_password=data.new_password,
    )
    return DataResponse(message="Password changed successfully", data={})


@router.get(
    "/me",
    response_model=DataResponse[UserResponse],
    summary="Get current authenticated user",
)
async def get_me(
    current_user: User = Depends(get_current_active_user),
) -> DataResponse[UserResponse]:
    """
    Returns the currently authenticated user's data.
    Requires valid access token in Authorization header.
    """
    return DataResponse(
        data=UserResponse.model_validate(current_user)
    )