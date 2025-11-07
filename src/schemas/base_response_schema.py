# app/schemas/base.py
from typing import Generic, Optional, TypeVar

from pydantic.generics import GenericModel

T = TypeVar("T")


class BaseResponseSchema(GenericModel, Generic[T]):

    success: bool = True
    message: Optional[str] = None
    data: Optional[T] = None

    model_config = {
        "from_attributes": True,
        "exclude_none": True,
    }

    def to_dict(self, exclude_none: Optional[bool] = True):
        return self.model_dump(exclude_none=exclude_none)
