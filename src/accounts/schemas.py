from typing import Optional
from ninja import Schema
from pydantic import EmailStr, Field


class RegisterSchema(Schema):
    username: str = Field(..., min_length=3, max_length=150)
    password: str = Field(..., min_length=8)
    email: Optional[EmailStr] = None


class AccountSchema(Schema):
    id: int
    username: str
    email: Optional[str] = None


class CustomObtainTokenSchema(Schema):
    username: str = None
    email: str = None
    password: str
