from ninja import Schema

class MarketSchema(Schema):
    name: str
    symbol: str
    slug: str
    rank: int
    price: int
    marketcap: int
    volume24h: int
    percentChange24h: int
    percentChange7d: int
    lastUpdated: str
    logo: str
