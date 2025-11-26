# app/schemas/base.py
from typing import Generic, Optional, TypeVar

from pydantic.generics import GenericModel

T = TypeVar("T")


class BaseResponseSchema(GenericModel, Generic[T]):
    # Indicates whether the API request was successful
    # True for success, False for failure
    success: bool = True

    # Human-readable message describing the result
    # Useful for displaying user feedback
    message: Optional[str] = None

    # returned schema for response
    data: Optional[T] = None

    model_config = {
        "from_attributes": True,
        "exclude_none": True,
    }

    def to_dict(self, exclude_none: Optional[bool] = True):
        return self.model_dump(exclude_none=exclude_none)
