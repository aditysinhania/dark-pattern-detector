from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Boolean, Enum as SAEnum
import enum
import uuid

from app.db.base import Base, TimestampMixin


class UserRole(str, enum.Enum):
    """
    Using Python enums for roles instead of raw strings.

    Why? If you typo "adimn" instead of "admin" in a string,
    it silently fails. An enum raises an error immediately.
    The 'str' inheritance means it serializes to a string in JSON.
    """
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"


class User(Base, TimestampMixin):
    """
    Core user model.

    Design decisions:
    - Email is the unique identifier, not username
      (easier for password reset, industry standard)
    - Password is never stored, only the bcrypt hash
    - is_verified tracks email verification
    - is_active allows soft-disabling accounts without deletion
    """
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,       # Index because we query by email constantly
        nullable=False,
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole),
        default=UserRole.USER,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Relationships — SQLAlchemy will load these when accessed
    scans: Mapped[list["Scan"]] = relationship(
        "Scan",
        back_populates="user",
        cascade="all, delete-orphan",  # Delete scans when user is deleted
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"