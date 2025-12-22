import aiohttp
from typing import Dict, List, Optional
from django.conf import settings


class CoinMarketCapService:
    """Service for interacting with CoinMarketCap API to fetch cryptocurrency data."""

    BASE_URL = "https://pro-api.coinmarketcap.com/v1"
    SANDBOX_URL = "https://sandbox-api.coinmarketcap.com/v1"

    def __init__(self, api_key: Optional[str] = None, use_sandbox: bool = False):
        """
        Initialize the CoinMarketCap service.

        Args:
            api_key: CoinMarketCap API key. If not provided, uses settings.CMC_API_KEY
            use_sandbox: Whether to use the sandbox environment
        """
        self.api_key = api_key or settings.CMC_API_KEY
        self.base_url = self.SANDBOX_URL if use_sandbox else self.BASE_URL
        self.headers = {
            "X-CMC_PRO_API_KEY": self.api_key,
            "Accept": "application/json",
        }

    async def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        Make a request to the CoinMarketCap API.

        Args:
            endpoint: API endpoint path
            params: Query parameters

        Returns:
            Response data as dictionary
        """
        url = f"{self.base_url}/{endpoint}"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    url,
                    headers=self.headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                    return data
            except aiohttp.ClientError as e:
                print(f"CoinMarketCap API request failed: {e}")
                return {"error": str(e)}
            except Exception as e:
                print(f"Unexpected error in CoinMarketCap request: {e}")
                return {"error": str(e)}

    async def get_cryptocurrency_quotes_latest(
        self,
        symbols: Optional[List[str]] = None,
        ids: Optional[List[int]] = None,
        convert: str = "USD",
    ) -> Dict:
        """
        Get the latest market quote for cryptocurrencies.

        Args:
            symbols: List of cryptocurrency symbols (e.g., ["BTC", "ETH"])
            ids: List of CoinMarketCap cryptocurrency IDs
            convert: Currency to convert to (default: USD)

        Returns:
            Dictionary containing quote data
        """
        params = {"convert": convert}

        if symbols:
            params["symbol"] = ",".join(symbols)
        elif ids:
            params["id"] = ",".join(map(str, ids))
        else:
            return {"error": "Either symbols or ids must be provided"}

        return await self._make_request("cryptocurrency/quotes/latest", params)

    async def get_cryptocurrency_info(
        self, symbols: Optional[List[str]] = None, ids: Optional[List[int]] = None
    ) -> Dict:
        """
        Get metadata information for cryptocurrencies.

        Args:
            symbols: List of cryptocurrency symbols
            ids: List of CoinMarketCap cryptocurrency IDs

        Returns:
            Dictionary containing cryptocurrency metadata
        """
        params = {}

        if symbols:
            params["symbol"] = ",".join(symbols)
        elif ids:
            params["id"] = ",".join(map(str, ids))
        else:
            return {"error": "Either symbols or ids must be provided"}

        return await self._make_request("cryptocurrency/info", params)

    async def get_cryptocurrency_listings_latest(
        self,
        start: int = 1,
        limit: int = 100,
        convert: str = "USD",
        sort: str = "market_cap",
        sort_dir: str = "desc",
    ) -> Dict:
        """
        Get a paginated list of all active cryptocurrencies with latest market data.

        Args:
            start: Starting position (default: 1)
            limit: Number of results (default: 100, max: 5000)
            convert: Currency to convert to (default: USD)
            sort: Sort field (market_cap, name, symbol, etc.)
            sort_dir: Sort direction (asc or desc)

        Returns:
            Dictionary containing listings data
        """
        params = {
            "start": start,
            "limit": limit,
            "convert": convert,
            "sort": sort,
            "sort_dir": sort_dir,
        }

        return await self._make_request("cryptocurrency/listings/latest", params)

    async def get_cryptocurrency_map(
        self, listing_status: str = "active", start: int = 1, limit: int = 5000
    ) -> Dict:
        """
        Get a mapping of all cryptocurrencies to unique CoinMarketCap IDs.

        Args:
            listing_status: active, inactive, or untracked
            start: Starting position
            limit: Number of results

        Returns:
            Dictionary containing cryptocurrency map
        """
        params = {
            "listing_status": listing_status,
            "start": start,
            "limit": limit,
        }

        return await self._make_request("cryptocurrency/map", params)

    async def get_price_conversion(
        self,
        amount: float,
        symbol: Optional[str] = None,
        id: Optional[int] = None,
        convert: str = "USD",
    ) -> Dict:
        """
        Convert an amount of one cryptocurrency to another currency.

        Args:
            amount: Amount to convert
            symbol: Source cryptocurrency symbol
            id: Source cryptocurrency ID
            convert: Target currency

        Returns:
            Dictionary containing conversion data
        """
        params = {
            "amount": amount,
            "convert": convert,
        }

        if symbol:
            params["symbol"] = symbol
        elif id:
            params["id"] = id
        else:
            return {"error": "Either symbol or id must be provided"}

        return await self._make_request("tools/price-conversion", params)

    async def get_global_metrics_latest(self, convert: str = "USD") -> Dict:
        """
        Get the latest global cryptocurrency market metrics.

        Args:
            convert: Currency to convert to

        Returns:
            Dictionary containing global metrics
        """
        params = {"convert": convert}
        return await self._make_request("global-metrics/quotes/latest", params)

    async def get_cryptocurrency_ohlcv_latest(
        self,
        symbols: Optional[List[str]] = None,
        ids: Optional[List[int]] = None,
        convert: str = "USD",
    ) -> Dict:
        """
        Get the latest OHLCV (Open, High, Low, Close, Volume) data.

        Args:
            symbols: List of cryptocurrency symbols
            ids: List of CoinMarketCap cryptocurrency IDs
            convert: Currency to convert to

        Returns:
            Dictionary containing OHLCV data
        """
        params = {"convert": convert}

        if symbols:
            params["symbol"] = ",".join(symbols)
        elif ids:
            params["id"] = ",".join(map(str, ids))
        else:
            return {"error": "Either symbols or ids must be provided"}

        return await self._make_request("cryptocurrency/ohlcv/latest", params)

    async def search_cryptocurrency(self, query: str, limit: int = 10) -> Dict:
        """
        Search for cryptocurrencies by name or symbol.

        This is a helper method that uses the map endpoint with filtering.

        Args:
            query: Search query (name or symbol)
            limit: Maximum number of results

        Returns:
            Dictionary containing search results
        """
        # Get the full map and filter client-side
        result = await self.get_cryptocurrency_map(limit=5000)

        if "error" in result or "data" not in result:
            return result

        # Filter results based on query
        query_lower = query.lower()
        filtered = [
            crypto
            for crypto in result.get("data", [])
            if query_lower in crypto.get("name", "").lower()
            or query_lower in crypto.get("symbol", "").lower()
        ]

        return {"data": filtered[:limit], "status": result.get("status", {})}
