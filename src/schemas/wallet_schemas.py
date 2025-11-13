from datetime import datetime
from typing import Optional

from ninja import Schema
from pydantic import EmailStr


class WalletModelCreationSchema(Schema):
    userId: Optional[str] = None
    deviceToken: Optional[str] = None
    privateKey: Optional[str] = None
    bs58PrivateKey: Optional[str] = None
    mnemonics: Optional[str] = None


class WalletAirdropSchema(Schema):
    address: Optional[str] = None
    amount: Optional[float] = 5.0


class WalletModelSchema(Schema):
    userId: Optional[str] = None
    email: Optional[EmailStr] = None
    emailIsConfirmed: Optional[bool] = None
    userId: Optional[str] = None
    isValid: Optional[bool] = None
    privateKey: Optional[str] = None
    bs58PrivateKey: Optional[str] = None
    address: Optional[str] = None
    mnemonics: Optional[str] = None
    balance: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    error: Optional[str] = None
    error: Optional[str] = None
    signature: Optional[str] = None
