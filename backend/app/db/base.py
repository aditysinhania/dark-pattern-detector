from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import DateTime, func
from datetime import datetime
import uuid


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models.

    Every table in our database inherits from this,
    which gives every table:
      - id: a UUID primary key (not an integer)
      - created_at: automatically set when record is created
      - updated_at: automatically updated on every change
    """
    pass


class TimestampMixin:
    """
    Mixin that adds created_at and updated_at to any model.

    Why a mixin instead of putting this in Base directly?
    Because mixins are composable. If we ever need a model
    without timestamps, we just don't include this mixin.

    SQLAlchemy's server_default uses the DATABASE's clock,
    not Python's — this matters in distributed systems where
    app servers may have slightly different clocks.
    """
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )