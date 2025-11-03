from typing import Optional
from datetime import datetime

from ninja import Schema
from pydantic import EmailStr


class WalletModelCreationSchema(Schema):
    email: Optional[EmailStr] = None
    email_confirmed: bool = False
    deviceToken: Optional[str] = None
    privateKey: Optional[str] = None
    bs58PrivateKey: Optional[str] = None
    address: Optional[str] = None
    mnemonics: Optional[str] = None
    balance: Optional[int] = None


class WalletModelSchema(Schema):
    email: Optional[EmailStr] = None
    email_confirmed: bool = False
    privateKey: Optional[str] = None
    bs58PrivateKey: Optional[str] = None
    address: Optional[str] = None
    mnemonics: Optional[str] = None
    balance: Optional[int] = None
    created_at: datetime
    updated_at: datetime
