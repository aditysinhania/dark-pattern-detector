from pydantic import BaseModel, EmailStr
from app.schemas.user import UserResponse


class LoginRequest(BaseModel):
    """
    OAuth2 password flow uses form data (not JSON) by default.
    We support JSON as well for our mobile and extension clients.
    """
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """
    The response after successful login or token refresh.

    access_token: short-lived (30 min), sent in Authorization header
    refresh_token: long-lived (7 days), used only to get new access tokens

    Why two tokens?
    If access tokens lived 7 days, a stolen token gives an attacker
    7 days of access. With 30-minute expiry, the window is small.
    Refresh tokens let users stay logged in without re-entering password.
    """
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class RegisterResponse(BaseModel):
    user: UserResponse
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    def validate_new_password(self) -> None:
        if len(self.new_password) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in self.new_password):
            raise ValueError("Must contain at least one uppercase letter")
        if not any(c.isdigit() for c in self.new_password):
            raise ValueError("Must contain at least one number")