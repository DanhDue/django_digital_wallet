from ninja import Schema


class TokenSchema(Schema):
    address: str
    mintAuthority: str
    supply: str
    freezeAuthority: str
    decimals: int
    isInitialized: bool
