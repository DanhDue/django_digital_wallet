from typing import Optional, List, Any

from ninja import Schema


class TransferTokenCreationSchema(Schema):
    bs58_private_key: Optional[str] = None
    recipient: Optional[str] = None

    # Amount transferred in token units (not accounting for decimals)
    # Example: 1000000 for 1 USDC (6 decimals)
    amount: Optional[float] = None

    # SPL Token mint address
    # Identifies the specific token contract
    mint_address: Optional[str] = None  # mint_address is None => Transfer Solana.

    # Token symbol (e.g., "SOL", "ZEO")
    # For display purposes
    symbol: Optional[str] = None

    # Token name (e.g., "Solana", "Zeno")
    # Full name of the token
    name: Optional[str] = None

    # Number of decimal places for the token
    # Used for proper amount formatting
    # Decimal of Sol is LAMPORTS_PER_SOL.
    # transfer_amount = 10_000_000_000  => 10 tokens with 9 decimals
    decimals: Optional[int] = None

    # Indicates whether the API request for calculate fee action or transfer action.
    # True for fee calculations, False for send_transaction(transfering doing).
    is_preview: Optional[bool] = True

    model_config = {
        "from_attributes": True,
        "exclude_none": True,
    }


class TokenAccountCreationSchema(Schema):
    bs58_private_key: Optional[str] = None
    mint_token: Optional[str] = None

    model_config = {
        "from_attributes": True,
        "exclude_none": True,
    }


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
    data_length: Optional[int] = None
    decimals: Optional[int] = None
    supply: Optional[int] = None
    is_initialized: Optional[int] = None
    mint_authority: Optional[str] = None
    update_authority: Optional[str] = None
    name: Optional[str] = None
    symbol: Optional[str] = None
    uri: Optional[str] = None
    is_mutable: Optional[bool] = None
    error: Optional[str] = None

    model_config = {
        "from_attributes": True,
        "exclude_none": True,
    }


class TokenMetaDataSchema(Schema):
    mint: Optional[str] = None
    name: Optional[str] = None
    symbol: Optional[str] = None
    uri: Optional[str] = None
    is_mutable: Optional[bool] = None
    update_authority: Optional[str] = None

    model_config = {
        "from_attributes": True,
        "exclude_none": True,
    }


class TokenAccountSchema(Schema):
    address: Optional[str] = None
    owner: Optional[str] = None
    amount: Optional[int] = None  # supple * decimals.

    is_initialized: Optional[int] = None

    mint: Optional[str] = None
    supply: Optional[int] = None
    decimals: Optional[int] = None

    mint_token: Optional[MintTokenSchema] = None

    account_owner: Optional[str] = None

    error: Optional[str] = None

    model_config = {
        "from_attributes": True,
        "exclude_none": True,
    }
