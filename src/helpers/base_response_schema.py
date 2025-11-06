# app/schemas/base.py
from typing import Generic, Optional, TypeVar

from pydantic.generics import GenericModel

T = TypeVar("T")  # type for generic data field


class BaseResponseSchema(GenericModel, Generic[T]):
    """Generic API response schema."""

    success: bool = True
    message: Optional[str] = None
    data: Optional[T] = None

    class Config:
        orm_mode = True
