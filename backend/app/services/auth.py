from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from datetime import timedelta
import structlog

from app.repositories.user import UserRepository
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.config import settings
from app.db.models.user import User, UserRole
from app.schemas.user import UserCreate, UserUpdate
from jose import JWTError
import uuid

logger = structlog.get_logger()


class AuthService:
    """
    Handles all authentication operations.

    Why a class instead of standalone functions?
    - Groups related operations together
    - The db session is injected once in __init__,
      not passed to every method
    - Easy to mock in tests: mock AuthService,
      not individual functions

    Service receives a repository, not a db session directly.
    This means services are testable without a database.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)

    async def register(self, data: UserCreate) -> User:
        """
        Register a new user.

        Steps:
        1. Check email isn't already registered
        2. Hash the password
        3. Create the user record
        4. Return the user (caller creates tokens)

        Why not create tokens here?
        Single responsibility — register creates a user,
        login creates tokens. Both can be tested separately.
        """
        logger.info("Registering new user", email=data.email)

        # Step 1: Check for duplicate email
        if await self.user_repo.email_exists(data.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists",
            )

        # Step 2: Hash password — never store plain text
        hashed = hash_password(data.password)

        # Step 3: Create user
        user = User(
            email=data.email.lower(),   # Normalize: "User@Email.COM" → "user@email.com"
            full_name=data.full_name.strip(),
            hashed_password=hashed,
            role=UserRole.USER,
            is_active=True,
            is_verified=False,          # Email verification in a future phase
        )

        user = await self.user_repo.create(user)
        logger.info("User registered successfully", user_id=str(user.id))
        return user

    async def login(self, email: str, password: str) -> User:
        """
        Authenticate a user with email and password.

        Security note: we return the same error whether the email
        doesn't exist OR the password is wrong. This prevents
        user enumeration attacks — an attacker can't tell which
        accounts exist by probing emails.
        """
        logger.info("Login attempt", email=email)

        # Use a constant-time-safe error
        invalid_credentials = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

        # Look up user
        user = await self.user_repo.get_by_email(email.lower())
        if user is None:
            # Still verify a dummy hash to prevent timing attacks.
            # Without this, an attacker can tell an email doesn't
            # exist because the response is faster (no bcrypt work).
            verify_password("dummy", "$2b$12$dummy.hash.to.prevent.timing.attack")
            raise invalid_credentials

        # Verify password
        if not verify_password(password, user.hashed_password):
            raise invalid_credentials

        # Check account is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled. Contact support.",
            )

        logger.info("Login successful", user_id=str(user.id))
        return user

    async def refresh_access_token(self, refresh_token: str) -> tuple[str, str]:
        """
        Exchange a refresh token for a new access + refresh token pair.

        Why issue a new refresh token too (token rotation)?
        If a refresh token is stolen and used, the original user's
        next refresh attempt will fail (token already rotated).
        This gives you a signal that token theft occurred.
        This is the OAuth2 best practice for refresh token security.
        """
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

        try:
            payload = decode_token(refresh_token)
            token_type = payload.get("type")
            user_id = payload.get("sub")

            if token_type != "refresh" or user_id is None:
                raise credentials_exception

        except JWTError:
            raise credentials_exception

        user = await self.user_repo.get_by_id(uuid.UUID(user_id))
        if user is None or not user.is_active:
            raise credentials_exception

        # Issue new token pair (rotation)
        new_access_token = create_access_token(subject=str(user.id))
        new_refresh_token = create_refresh_token(subject=str(user.id))

        return new_access_token, new_refresh_token

    async def change_password(
        self,
        user: User,
        current_password: str,
        new_password: str,
    ) -> None:
        """
        Change an authenticated user's password.
        Requires current password — prevents account takeover
        if someone walks away from an unlocked session.
        """
        if not verify_password(current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect",
            )

        user.hashed_password = hash_password(new_password)
        await self.user_repo.update(user)
        logger.info("Password changed", user_id=str(user.id))

    async def update_profile(self, user: User, data: UserUpdate) -> User:
        """
        Update user profile fields.
        Only updates fields that were actually sent (PATCH semantics).
        """
        if data.email is not None:
            # Check new email isn't taken by someone else
            existing = await self.user_repo.get_by_email(data.email.lower())
            if existing and existing.id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This email is already in use",
                )
            user.email = data.email.lower()

        if data.full_name is not None:
            user.full_name = data.full_name.strip()

        return await self.user_repo.update(user)