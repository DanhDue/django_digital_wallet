from typing import Optional

from ninja import Schema


class TokenSchema(Schema):
    address: str
    mintAuthority: str
    supply: str
    freezeAuthority: str
    decimals: int
    isInitialized: bool

    model_config = {
        "from_attributes": True,
        "exclude_none": True,
    }


class MintTokenSchema(Schema):
    address: Optional[str] = None
    decimals: Optional[int] = None
    supply: Optional[int] = None
    is_initialized: Optional[bool] = None
    mint_authority: Optional[str] = None
    freeze_authority: Optional[str] = None
    error: Optional[str] = None

    model_config = {
        "from_attributes": True,
        "exclude_none": True,
    }
