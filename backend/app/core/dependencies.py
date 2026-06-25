from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError
import uuid

from app.db.session import get_db
from app.core.security import decode_token
from app.db.models.user import User, UserRole
from app.repositories.user import UserRepository

# This tells FastAPI where to find the token.
# When a route uses get_current_user, Swagger UI automatically
# shows an "Authorize" button — great for demos.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    The core authentication dependency.

    Any route that includes this dependency is protected.
    FastAPI automatically:
    1. Extracts the Bearer token from the Authorization header
    2. Calls this function
    3. If it raises HTTPException, returns 401 to the client
    4. If it returns a User, injects it into the route handler

    This is dependency injection — your routes declare WHAT they
    need, FastAPI handles HOW to get it.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(token)
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")

        if user_id is None or token_type != "access":
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(uuid.UUID(user_id))

    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Ensures the user is active.
    Use this for most protected routes.
    """
    return current_user


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Admin-only dependency.
    Use this for admin panel routes.

    Composing dependencies: require_admin depends on
    get_current_user, which depends on get_db and oauth2_scheme.
    FastAPI resolves the whole chain automatically.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user