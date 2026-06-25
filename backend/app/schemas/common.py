from pydantic import BaseModel
from typing import TypeVar, Generic, Any
from datetime import datetime
import uuid


T = TypeVar("T")


class BaseResponse(BaseModel):
    """
    Every API response wraps data in a consistent envelope.

    Why an envelope? Without it, a success response might be:
        {"email": "...", "id": "..."}
    And an error response:
        {"detail": "Not found"}

    With an envelope, every response has the same shape:
        {"success": true, "data": {...}, "message": "..."}

    This makes frontend code simpler — you always check
    response.success before reading response.data.
    Clients never need to guess the response shape.
    """
    success: bool = True
    message: str = "OK"


class DataResponse(BaseResponse, Generic[T]):
    """
    Response that wraps a single data object.

    Generic[T] means DataResponse[UserResponse] tells
    the type system (and Swagger) exactly what shape
    data will be. This gives you full type safety
    and accurate API documentation for free.
    """
    data: T


class PaginatedResponse(BaseResponse, Generic[T]):
    """
    Response for paginated list endpoints.

    Always return pagination metadata with lists.
    Without it, the client doesn't know if they've
    reached the last page.
    """
    data: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class ErrorResponse(BaseModel):
    """
    Consistent error shape.
    Used in exception handlers.
    """
    success: bool = False
    message: str
    detail: Any = None