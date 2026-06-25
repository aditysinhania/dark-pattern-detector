from pydantic import BaseModel, EmailStr, field_validator, ConfigDict
from datetime import datetime
from typing import Optional
import uuid

from app.db.models.user import UserRole


class UserBase(BaseModel):
    """
    Fields shared between create and update schemas.

    Why split into Base/Create/Update/Response?
    - Create needs password, Response must never include it
    - Update makes all fields optional (PATCH semantics)
    - Response adds server-generated fields (id, created_at)

    Duplicating fields across one class would mean
    accidentally exposing the password in responses.
    """
    email: EmailStr
    full_name: str

    @field_validator("full_name")
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Full name cannot be empty")
        if len(v) < 2:
            raise ValueError("Full name must be at least 2 characters")
        return v


class UserCreate(UserBase):
    """
    Schema for POST /auth/register.
    Password validation happens here — never in the model.
    """
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        return v


class UserUpdate(BaseModel):
    """
    Schema for PATCH /users/me.
    Every field is Optional — clients send only what they want to change.
    This is PATCH semantics vs PUT (which requires all fields).
    """
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None

    @field_validator("full_name")
    @classmethod
    def name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if len(v) < 2:
                raise ValueError("Full name must be at least 2 characters")
        return v


class UserResponse(BaseModel):
    """
    Schema for returning user data to clients.

    CRITICAL: hashed_password is NOT in this schema.
    Pydantic only serializes fields declared here —
    the password hash can never leak into a response.

    model_config with from_attributes=True lets Pydantic
    read from SQLAlchemy model instances directly.
    Without this, you'd have to convert to dict manually.
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime


class UserProfileResponse(UserResponse):
    """
    Extended profile with scan statistics.
    Used in the profile page — not in auth responses.
    """
    total_scans: int = 0
    total_patterns_found: int = 0