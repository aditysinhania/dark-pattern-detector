from datetime import datetime, timedelta, timezone
from typing import Any
from passlib.context import CryptContext
from jose import JWTError, jwt

from app.core.config import settings


# CryptContext configures our hashing algorithm.
# bcrypt is the industry standard for password hashing because:
# - It's intentionally slow (configurable work factor)
# - It includes a salt automatically
# - It's resistant to GPU-based brute force attacks
# 
# Why NOT md5/sha256? They're fast — exactly what you don't want
# for passwords. A GPU can compute billions of SHA256 hashes/second.
# bcrypt by design takes ~100ms per hash.
#
# deprecated="auto" means if we upgrade algorithms in future,
# old hashes are automatically detected and re-hashed on login.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hash a plain text password.
    Never store plain text passwords. Ever.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain text password against its hash.
    Uses constant-time comparison to prevent timing attacks.
    
    Timing attack: if comparison short-circuits on first wrong
    character, an attacker can guess passwords character by
    character by measuring response time. bcrypt prevents this.
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    subject: str,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """
    Create a JWT access token.

    JWT structure: header.payload.signature
    - Header: algorithm type
    - Payload: claims (user_id, expiry, roles)
    - Signature: HMAC of header+payload using SECRET_KEY

    Why JWT over sessions?
    - Stateless: no server-side session storage needed
    - Scalable: any server can verify the token
    - Works across mobile, web, and extension clients
    - Self-contained: user role is in the token, no DB lookup needed

    Limitation: JWTs can't be revoked before expiry.
    Mitigation: short expiry (30 min) + refresh tokens.
    This is a common interview trade-off discussion.
    """
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    payload = {
        "sub": subject,          # Subject: the user's ID
        "exp": expire,           # Expiry timestamp
        "iat": datetime.now(timezone.utc),  # Issued at
        "type": "access",        # Token type
    }

    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_refresh_token(subject: str) -> str:
    """
    Refresh tokens have longer expiry and are used ONLY
    to get new access tokens — not to access resources.

    This two-token pattern means:
    - Access tokens are short-lived (30 min) — limits damage if stolen
    - Refresh tokens are long-lived (7 days) — user stays logged in
    - Refresh tokens can be stored in an httpOnly cookie
      (JS can't read it — XSS protection)
    """
    return create_access_token(
        subject=subject,
        expires_delta=timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        extra_claims={"type": "refresh"},
    )


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT token.
    Raises JWTError if token is invalid, expired, or tampered with.
    """
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )