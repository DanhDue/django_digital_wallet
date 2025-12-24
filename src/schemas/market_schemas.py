from typing import Optional, List
from ninja import Schema


class CryptocurrencyListingsRequestSchema(Schema):
    """Schema for cryptocurrency listings API request parameters."""

    # Starting position (default: 1)
    start: Optional[int] = 1

    # Number of results to return (default: 100, max: 5000)
    limit: Optional[int] = 100

    # Currency to convert to (default: USD)
    convert: Optional[str] = "USD"

    # Sort field: market_cap, name, symbol, date_added, market_cap_strict,
    # price, circulating_supply, total_supply, max_supply, num_market_pairs, volume_24h, percent_change_1h,
    # percent_change_24h, percent_change_7d
    sort: Optional[str] = "market_cap"

    # Sort direction: asc or desc (default: desc)
    sort_dir: Optional[str] = "desc"

    # Whether to include the full metadata (default: True)
    include_metadata: Optional[bool] = True

    # Whether to include the latest OHLCV data (default: True)
    include_ohlcv: Optional[bool] = True


class CryptocurrencyInfoRequestSchema(Schema):
    """Schema for cryptocurrency quotes API request parameters."""

    # List of cryptocurrency symbols (e.g., "BTC,ETH")
    symbols: Optional[str] = None

    # List of CoinMarketCap cryptocurrency IDs (comma-separated)
    ids: Optional[str] = None

    # Currency to convert to (default: USD)
    convert: Optional[str] = "USD"


class PriceConversionRequestSchema(Schema):
    """Schema for price conversion API request parameters."""

    # Amount to convert
    amount: float

    # Source cryptocurrency symbol
    symbol: Optional[str] = None

    # Source cryptocurrency ID
    id: Optional[int] = None

    # Target currency (default: USD)
    convert: Optional[str] = "USD"


class GlobalMetricsRequestSchema(Schema):
    """Schema for global metrics API request parameters."""

    # Currency to convert to (default: USD)
    convert: Optional[str] = "USD"


class CryptocurrencyMapRequestSchema(Schema):
    """Schema for cryptocurrency map API request parameters."""

    # Listing status: active, inactive, or untracked
    listing_status: Optional[str] = "active"

    # Starting position
    start: Optional[int] = 1

    # Number of results
    limit: Optional[int] = 5000


class CryptocurrencySearchRequestSchema(Schema):
    """Schema for cryptocurrency search API request parameters."""

    # Search query (name or symbol)
    query: str

    # Maximum number of results
    limit: Optional[int] = 10


class CryptocurrencyOHLCVRequestSchema(Schema):
    """Schema for cryptocurrency OHLCV API request parameters."""

    # List of cryptocurrency symbols (e.g., "BTC,ETH")
    symbols: Optional[str] = None

    # List of CoinMarketCap cryptocurrency IDs (comma-separated)
    ids: Optional[str] = None

    # Currency to convert to (default: USDT for Binance compatibility)
    convert: Optional[str] = "USDT"


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
