from ninja import Schema


class TransactionSchema(Schema):
    id: int
    sender: str
    receiver: str
    token: str
    symbol: str
    blockTime: str
    amount: int
    fee: int
    signature: str
    direction: str
    status: str
