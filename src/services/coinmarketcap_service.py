import asyncio
import aiohttp
from typing import Dict, List, Optional
from django.conf import settings
from . import market_constants as mc
from utils.cache import SearchCache


class CoinMarketCapService:
    """Service for interacting with CoinMarketCap API to fetch cryptocurrency data."""

    BASE_URL = "https://pro-api.coinmarketcap.com/v1"
    SANDBOX_URL = "https://sandbox-api.coinmarketcap.com/v1"
    BINANCE_BASE_URL = "https://api.binance.com/api/v3"

    def __init__(self, api_key: Optional[str] = None, use_sandbox: bool = False):
        """
        Initialize the CoinMarketCap service.

        Args:
            api_key: CoinMarketCap API key. If not provided, uses settings.CMC_API_KEY
            use_sandbox: Whether to use the sandbox environment
        """
        self.api_key = api_key or settings.CMC_API_KEY
        self.api_base_url = self.SANDBOX_URL if use_sandbox else self.BASE_URL
        self.headers = {
            "X-CMC_PRO_API_KEY": self.api_key,
            "Accept": "application/json",
        }
        self.metadata_cache = SearchCache(
            cache_dir="metadata_cache", default_ttl=3600 * 24 * 7
        )

    async def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        Make a request to the CoinMarketCap API.

        Args:
            endpoint: API endpoint path
            params: Query parameters

        Returns:
            Response data as dictionary
        """
        url = f"{self.api_base_url}/{endpoint}"

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
                return {mc.KEY_ERROR: str(e)}
            except Exception as e:
                print(f"Unexpected error in CoinMarketCap request: {e}")
                return {mc.KEY_ERROR: str(e)}

    def _build_quote_data(self, crypto: Dict, quote_data: Dict, timestamp: str) -> Dict:
        """Build cryptocurrency data object with quote fields."""
        return {
            mc.KEY_TIMESTAMP: timestamp,
            mc.KEY_ID: crypto.get(mc.KEY_ID),
            mc.KEY_NAME: crypto.get(mc.KEY_NAME),
            mc.KEY_SYMBOL: crypto.get(mc.KEY_SYMBOL),
            mc.KEY_SLUG: crypto.get(mc.KEY_SLUG),
            mc.KEY_NUM_MARKET_PAIRS: crypto.get(mc.KEY_NUM_MARKET_PAIRS),
            mc.KEY_DATE_ADDED: crypto.get(mc.KEY_DATE_ADDED),
            mc.KEY_MAX_SUPPLY: crypto.get(mc.KEY_MAX_SUPPLY),
            mc.KEY_CIRCULATING_SUPPLY: crypto.get(mc.KEY_CIRCULATING_SUPPLY),
            mc.KEY_TOTAL_SUPPLY: crypto.get(mc.KEY_TOTAL_SUPPLY),
            mc.KEY_IS_ACTIVE: crypto.get(mc.KEY_IS_ACTIVE),
            mc.KEY_INFINITE_SUPPLY: crypto.get(mc.KEY_INFINITE_SUPPLY),
            mc.KEY_MINTED_MARKET_CAP: crypto.get(mc.KEY_MINTED_MARKET_CAP),
            mc.KEY_PLATFORM: crypto.get(mc.KEY_PLATFORM),
            mc.KEY_CMC_RANK: crypto.get(mc.KEY_CMC_RANK),
            mc.KEY_IS_FIAT: crypto.get(mc.KEY_IS_FIAT),
            mc.KEY_SELF_REPORTED_CIRC_SUPPLY: crypto.get(
                mc.KEY_SELF_REPORTED_CIRC_SUPPLY
            ),
            mc.KEY_SELF_REPORTED_MARKET_CAP: crypto.get(
                mc.KEY_SELF_REPORTED_MARKET_CAP
            ),
            mc.KEY_TVL_RATIO: crypto.get(mc.KEY_TVL_RATIO),
            mc.KEY_LAST_UPDATED: crypto.get(mc.KEY_LAST_UPDATED),
            # Quote fields
            mc.KEY_PRICE: quote_data.get(mc.KEY_PRICE),
            mc.KEY_VOLUME_24H: quote_data.get(mc.KEY_VOLUME_24H),
            mc.KEY_VOLUME_CHANGE_24H: quote_data.get(mc.KEY_VOLUME_CHANGE_24H),
            mc.KEY_PERCENT_CHANGE_1H: quote_data.get(mc.KEY_PERCENT_CHANGE_1H),
            mc.KEY_PERCENT_CHANGE_24H: quote_data.get(mc.KEY_PERCENT_CHANGE_24H),
            mc.KEY_PERCENT_CHANGE_7D: quote_data.get(mc.KEY_PERCENT_CHANGE_7D),
            mc.KEY_PERCENT_CHANGE_30D: quote_data.get(mc.KEY_PERCENT_CHANGE_30D),
            mc.KEY_PERCENT_CHANGE_60D: quote_data.get(mc.KEY_PERCENT_CHANGE_60D),
            mc.KEY_PERCENT_CHANGE_90D: quote_data.get(mc.KEY_PERCENT_CHANGE_90D),
            mc.KEY_MARKET_CAP: quote_data.get(mc.KEY_MARKET_CAP),
            mc.KEY_MARKET_CAP_DOMINANCE: quote_data.get(mc.KEY_MARKET_CAP_DOMINANCE),
            mc.KEY_FULLY_DILUTED_MARKET_CAP: quote_data.get(
                mc.KEY_FULLY_DILUTED_MARKET_CAP
            ),
            mc.KEY_TVL: quote_data.get(mc.KEY_TVL),
        }

    def _merge_metadata(self, combined_data: Dict, info_response: Dict) -> None:
        """Merge metadata from info response into combined data."""
        if mc.KEY_DATA not in info_response or mc.KEY_ERROR in info_response:
            return

        for symbol, info in info_response.get(mc.KEY_DATA, {}).items():
            if symbol in combined_data:
                combined_data[symbol].update(
                    {
                        mc.KEY_CATEGORY: info.get(mc.KEY_CATEGORY),
                        mc.KEY_DESCRIPTION: info.get(mc.KEY_DESCRIPTION),
                        mc.KEY_LOGO: info.get(mc.KEY_LOGO),
                        mc.KEY_SUBREDDIT: info.get(mc.KEY_SUBREDDIT),
                        mc.KEY_NOTICE: info.get(mc.KEY_NOTICE),
                        mc.KEY_URLS: info.get(mc.KEY_URLS),
                        mc.KEY_TWITTER_USERNAME: info.get(mc.KEY_TWITTER_USERNAME),
                        mc.KEY_IS_HIDDEN: info.get(mc.KEY_IS_HIDDEN),
                        mc.KEY_DATE_LAUNCHED: info.get(mc.KEY_DATE_LAUNCHED),
                        mc.KEY_CONTRACT_ADDRESS: info.get(mc.KEY_CONTRACT_ADDRESS),
                        mc.KEY_SELF_REPORTED_TAGS: info.get(mc.KEY_SELF_REPORTED_TAGS),
                    }
                )

    async def get_cryptocurrency_details(
        self,
        symbols: Optional[List[str]] = None,
        ids: Optional[List[int]] = None,
        convert: str = "USD",
    ) -> Dict:
        """
        Get comprehensive cryptocurrency data including quotes and metadata.

        This method combines data from both the quotes and info endpoints to provide
        a complete view of cryptocurrencies including price data and metadata.

        Args:
            symbols: List of cryptocurrency symbols (e.g., ["BTC", "ETH"])
            ids: List of CoinMarketCap cryptocurrency IDs
            convert: Currency to convert to (default: USD)

        Returns:
            Dictionary containing combined quote and metadata, keyed by symbol
        """
        if not symbols and not ids:
            return {mc.KEY_ERROR: mc.ERROR_SYMBOLS_OR_IDS_REQUIRED}

        # Prepare parameters for both requests
        quote_params = {mc.KEY_CONVERT: convert}
        info_params = {}

        if symbols:
            quote_params[mc.KEY_SYMBOL] = ",".join(symbols)
            info_params[mc.KEY_SYMBOL] = ",".join(symbols)
        elif ids:
            quote_params[mc.KEY_ID] = ",".join(map(str, ids))
            info_params[mc.KEY_ID] = ",".join(map(str, ids))

        # Fetch quote data and metadata concurrently
        quotes_response, info_response = await asyncio.gather(
            self._make_request("cryptocurrency/quotes/latest", quote_params),
            self._make_request("cryptocurrency/info", info_params),
        )

        # Handle error responses
        if mc.KEY_ERROR in quotes_response or mc.KEY_DATA not in quotes_response:
            return quotes_response

        # Extract timestamp and parse quote data
        timestamp = quotes_response.get(mc.KEY_STATUS, {}).get(mc.KEY_TIMESTAMP)
        combined_data = {}

        for symbol, crypto in quotes_response.get(mc.KEY_DATA, {}).items():
            quote_data = crypto.get(mc.KEY_QUOTE, {}).get(convert, {})
            combined_data[symbol] = self._build_quote_data(
                crypto, quote_data, timestamp
            )

        # Merge metadata
        self._merge_metadata(combined_data, info_response)

        return combined_data

    async def get_cryptocurrency_listings_latest(
        self,
        start: int = 1,
        limit: int = 100,
        convert: str = "USD",
        sort: str = "market_cap",
        sort_dir: str = "desc",
        include_metadata: bool = True,
        include_ohlcv: bool = True,
    ) -> List[Dict]:
        """
        Get a paginated list of all active cryptocurrencies with latest market data.

        Args:
            start: Starting position (default: 1)
            limit: Number of results (default: 100, max: 5000)
            convert: Currency to convert to (default: USD)
            sort: Sort field (market_cap, name, symbol, etc.)
            sort_dir: Sort direction (asc or desc)
            include_metadata: Whether to include the full metadata (default: True)
            include_ohlcv: Whether to include the latest OHLCV data (default: True)

        Returns:
            List of dictionaries containing flattened cryptocurrency data with quote information
        """
        params = {
            mc.KEY_START: start,
            mc.KEY_LIMIT: limit,
            mc.KEY_CONVERT: convert,
            mc.KEY_SORT: sort,
            mc.KEY_SORT_DIR: sort_dir,
        }

        response = await self._make_request("cryptocurrency/listings/latest", params)

        # Handle error responses
        if mc.KEY_ERROR in response or mc.KEY_DATA not in response:
            return []

        # Extract timestamp from status
        timestamp = response.get(mc.KEY_STATUS, {}).get(mc.KEY_TIMESTAMP)
        cryptos = response.get(mc.KEY_DATA, [])

        # Fetch metadata and OHLCV if requested
        metadata_map = {}
        ohlcv_map = {}

        tasks = []
        if include_metadata and cryptos:
            tasks.append(self._get_metadata_with_cache(cryptos))
        else:
            tasks.append(asyncio.sleep(0, result={}))

        if include_ohlcv and cryptos:
            symbols = [crypto.get(mc.KEY_SYMBOL) for crypto in cryptos]
            # Use Binance for OHLCV since CMC OHLCV is often paid/restricted
            tasks.append(self.get_binance_ohlcv_latest(symbols=symbols, convert="USDT"))
        else:
            tasks.append(asyncio.sleep(0, result={}))

        metadata_map, ohlcv_response = await asyncio.gather(*tasks)

        if include_ohlcv:
            ohlcv_map = ohlcv_response

        # Parse and flatten each cryptocurrency
        return [
            self._flatten_crypto_data(
                crypto, convert, timestamp, metadata_map, ohlcv_map
            )
            for crypto in cryptos
        ]

    async def _get_metadata_with_cache(self, cryptos: List[Dict]) -> Dict[int, Dict]:
        """Fetch metadata from cache or API for a list of cryptocurrencies."""
        metadata_map = {}
        ids_to_fetch = []

        for crypto in cryptos:
            crypto_id = crypto.get(mc.KEY_ID)
            # Use a different partition 'cmc_metadata' for full metadata
            cached_data = self.metadata_cache.get(str(crypto_id), "cmc_metadata")
            if cached_data and isinstance(cached_data, list) and cached_data:
                metadata_map[crypto_id] = cached_data[0]
            else:
                ids_to_fetch.append(str(crypto_id))

        if not ids_to_fetch:
            return metadata_map

        # Fetch missing from API
        info_response = await self._make_request(
            "cryptocurrency/info", {mc.KEY_ID: ",".join(ids_to_fetch)}
        )

        if mc.KEY_DATA in info_response and mc.KEY_ERROR not in info_response:
            for crypto_id, info in info_response.get(mc.KEY_DATA, {}).items():
                cid = int(crypto_id)
                # Store the whole info dict (metadata)
                metadata_map[cid] = info
                # Store in cache (as a list containing the dict)
                self.metadata_cache.put(str(cid), [info], "cmc_metadata")

        return metadata_map

    def _flatten_crypto_data(
        self,
        crypto: Dict,
        convert: str,
        timestamp: str,
        metadata_map: Dict[int, Dict],
        ohlcv_map: Dict[str, Dict] = None,
    ) -> Dict:
        """Flatten nested cryptocurrency data into a single dictionary."""
        quote_data = crypto.get(mc.KEY_QUOTE, {}).get(convert, {})
        crypto_id = crypto.get(mc.KEY_ID)

        flattened = {
            mc.KEY_TIMESTAMP: timestamp,
            mc.KEY_ID: crypto_id,
            mc.KEY_NAME: crypto.get(mc.KEY_NAME),
            mc.KEY_SYMBOL: crypto.get(mc.KEY_SYMBOL),
            mc.KEY_SLUG: crypto.get(mc.KEY_SLUG),
            mc.KEY_NUM_MARKET_PAIRS: crypto.get(mc.KEY_NUM_MARKET_PAIRS),
            mc.KEY_DATE_ADDED: crypto.get(mc.KEY_DATE_ADDED),
            mc.KEY_MAX_SUPPLY: crypto.get(mc.KEY_MAX_SUPPLY),
            mc.KEY_CIRCULATING_SUPPLY: crypto.get(mc.KEY_CIRCULATING_SUPPLY),
            mc.KEY_TOTAL_SUPPLY: crypto.get(mc.KEY_TOTAL_SUPPLY),
            mc.KEY_INFINITE_SUPPLY: crypto.get(mc.KEY_INFINITE_SUPPLY),
            mc.KEY_MINTED_MARKET_CAP: crypto.get(mc.KEY_MINTED_MARKET_CAP),
            mc.KEY_PLATFORM: crypto.get(mc.KEY_PLATFORM),
            mc.KEY_CMC_RANK: crypto.get(mc.KEY_CMC_RANK),
            mc.KEY_LAST_UPDATED: crypto.get(mc.KEY_LAST_UPDATED),
            # Add all quote fields
            mc.KEY_PRICE: quote_data.get(mc.KEY_PRICE),
            mc.KEY_VOLUME_24H: quote_data.get(mc.KEY_VOLUME_24H),
            mc.KEY_VOLUME_CHANGE_24H: quote_data.get(mc.KEY_VOLUME_CHANGE_24H),
            mc.KEY_PERCENT_CHANGE_1H: quote_data.get(mc.KEY_PERCENT_CHANGE_1H),
            mc.KEY_PERCENT_CHANGE_24H: quote_data.get(mc.KEY_PERCENT_CHANGE_24H),
            mc.KEY_PERCENT_CHANGE_7D: quote_data.get(mc.KEY_PERCENT_CHANGE_7D),
            mc.KEY_PERCENT_CHANGE_30D: quote_data.get(mc.KEY_PERCENT_CHANGE_30D),
            mc.KEY_PERCENT_CHANGE_60D: quote_data.get(mc.KEY_PERCENT_CHANGE_60D),
            mc.KEY_PERCENT_CHANGE_90D: quote_data.get(mc.KEY_PERCENT_CHANGE_90D),
            mc.KEY_MARKET_CAP: quote_data.get(mc.KEY_MARKET_CAP),
            mc.KEY_MARKET_CAP_DOMINANCE: quote_data.get(mc.KEY_MARKET_CAP_DOMINANCE),
            mc.KEY_FULLY_DILUTED_MARKET_CAP: quote_data.get(
                mc.KEY_FULLY_DILUTED_MARKET_CAP
            ),
            mc.KEY_TVL: quote_data.get(mc.KEY_TVL),
        }

        # Merge metadata if available
        if crypto_id in metadata_map:
            info = metadata_map[crypto_id]
            flattened.update(
                {
                    mc.KEY_LOGO: info.get(mc.KEY_LOGO),
                    mc.KEY_DESCRIPTION: info.get(mc.KEY_DESCRIPTION),
                    mc.KEY_CATEGORY: info.get(mc.KEY_CATEGORY),
                    mc.KEY_NOTICE: info.get(mc.KEY_NOTICE),
                    mc.KEY_URLS: info.get(mc.KEY_URLS),
                    mc.KEY_DATE_LAUNCHED: info.get(mc.KEY_DATE_LAUNCHED),
                    mc.KEY_SELF_REPORTED_CIRC_SUPPLY: info.get(
                        mc.KEY_SELF_REPORTED_CIRC_SUPPLY
                    ),
                    mc.KEY_SELF_REPORTED_MARKET_CAP: info.get(
                        mc.KEY_SELF_REPORTED_MARKET_CAP
                    ),
                }
            )

        # Merge OHLCV if available
        if ohlcv_map:
            # Binance OHLCV returns data keyed by symbol
            symbol = crypto.get(mc.KEY_SYMBOL)
            if symbol in ohlcv_map:
                ohlcv_data = ohlcv_map[symbol]
                if mc.KEY_ERROR not in ohlcv_data:
                    flattened.update(
                        {
                            mc.KEY_OPEN: ohlcv_data.get(mc.KEY_OPEN),
                            mc.KEY_HIGH: ohlcv_data.get(mc.KEY_HIGH),
                            mc.KEY_LOW: ohlcv_data.get(mc.KEY_LOW),
                            mc.KEY_CLOSE: ohlcv_data.get(mc.KEY_CLOSE),
                            mc.KEY_VOLUME: ohlcv_data.get(mc.KEY_VOLUME),
                            mc.KEY_OPEN_TIME: ohlcv_data.get(mc.KEY_OPEN_TIME),
                            mc.KEY_CLOSE_TIME: ohlcv_data.get(mc.KEY_CLOSE_TIME),
                            mc.KEY_QUOTE_ASSET_VOLUME: ohlcv_data.get(
                                mc.KEY_QUOTE_ASSET_VOLUME
                            ),
                            mc.KEY_NUMBER_OF_TRADES: ohlcv_data.get(
                                mc.KEY_NUMBER_OF_TRADES
                            ),
                        }
                    )

        return flattened

    async def get_cryptocurrency_map(
        self, listing_status: str = "active", start: int = 1, limit: int = 5000
    ) -> List[Dict]:
        """
        Get a mapping of all cryptocurrencies to unique CoinMarketCap IDs.

        Args:
            listing_status: active, inactive, or untracked
            start: Starting position
            limit: Number of results

        Returns:
            List of cryptocurrency map data
        """
        params = {
            mc.KEY_LISTING_STATUS: listing_status,
            mc.KEY_START: start,
            mc.KEY_LIMIT: limit,
        }

        response = await self._make_request("cryptocurrency/map", params)

        # Handle error responses
        if mc.KEY_ERROR in response or mc.KEY_DATA not in response:
            return []

        # Return just the data array
        return response.get(mc.KEY_DATA, [])

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
            Dictionary containing flattened conversion data
        """
        params = {
            mc.KEY_AMOUNT: amount,
            mc.KEY_CONVERT: convert,
        }

        if symbol:
            params[mc.KEY_SYMBOL] = symbol
        elif id:
            params[mc.KEY_ID] = id
        else:
            return {mc.KEY_ERROR: mc.ERROR_SYMBOLS_OR_IDS_REQUIRED}

        response = await self._make_request("tools/price-conversion", params)

        # Handle error responses
        if mc.KEY_ERROR in response or mc.KEY_DATA not in response:
            return response

        # Extract timestamp from status
        timestamp = response.get(mc.KEY_STATUS, {}).get(mc.KEY_TIMESTAMP)

        # Extract data
        data = response.get(mc.KEY_DATA, {})
        quote_data = data.get(mc.KEY_QUOTE, {}).get(convert, {})

        # Create flattened object
        flattened_data = {
            mc.KEY_TIMESTAMP: timestamp,
            mc.KEY_ID: data.get(mc.KEY_ID),
            mc.KEY_SYMBOL: data.get(mc.KEY_SYMBOL),
            mc.KEY_NAME: data.get(mc.KEY_NAME),
            mc.KEY_AMOUNT: data.get(mc.KEY_AMOUNT),
            mc.KEY_LAST_UPDATED: data.get(mc.KEY_LAST_UPDATED),
            mc.KEY_CONVERT: convert,
            mc.KEY_PRICE: quote_data.get(mc.KEY_PRICE),
        }

        return flattened_data

    async def get_global_metrics_latest(self, convert: str = "USD") -> Dict:
        """
        Get the latest global cryptocurrency market metrics.

        Args:
            convert: Currency to convert to

        Returns:
            Dictionary containing global metrics
        """
        params = {mc.KEY_CONVERT: convert}
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
        params = {mc.KEY_CONVERT: convert}

        if symbols:
            params[mc.KEY_SYMBOL] = ",".join(symbols)
        elif ids:
            params[mc.KEY_ID] = ",".join(map(str, ids))
        else:
            return {mc.KEY_ERROR: mc.ERROR_SYMBOLS_OR_IDS_REQUIRED}

        return await self._make_request("cryptocurrency/ohlcv/latest", params)

    async def search_cryptocurrency(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search for cryptocurrencies by name or symbol.

        This is a helper method that uses the map endpoint with filtering.

        Args:
            query: Search query (name or symbol)
            limit: Maximum number of results

        Returns:
            List of search results
        """
        # Get the full map and filter client-side
        result = await self.get_cryptocurrency_map(limit=5000)

        # If result is empty (error case), return empty list
        if not result:
            return []

        # Filter results based on query
        query_lower = query.lower()
        filtered = [
            crypto
            for crypto in result
            if query_lower in crypto.get(mc.KEY_NAME, "").lower()
            or query_lower in crypto.get(mc.KEY_SYMBOL, "").lower()
        ]

        return filtered[:limit]

    async def get_binance_ohlcv_latest(
        self,
        symbols: List[str],
        convert: str = "USDT",
        interval: str = "1d",
        limit: int = 1,
    ) -> Dict:
        """
        Get the latest OHLCV (Open, High, Low, Close, Volume) data from Binance.

        Args:
            symbols: List of cryptocurrency symbols (e.g., ["BTC", "ETH"])
            convert: Quote currency for trading pairs (default: USDT)
                    Supported values: USDT, BTC, BUSD, BNB, ETH, and other Binance quote assets
                    Example: symbols=["ETH"] with convert="USDT" fetches ETHUSDT pair
            interval: Kline interval (1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w, 1M)
            limit: Number of klines to return (default: 1 for latest)

        Returns:
            Dictionary containing OHLCV data for each symbol
        """

        if not symbols:
            return {mc.KEY_ERROR: "Binance API requires cryptocurrency symbols"}

        async with aiohttp.ClientSession() as session:
            tasks = [
                self._fetch_single_binance_ohlcv(
                    session, symbol, convert, interval, limit
                )
                for symbol in symbols
            ]
            results = await asyncio.gather(*tasks)

        # Merge results into a single dictionary
        combined_result = {}
        for symbol, data in zip(symbols, results):
            combined_result[symbol] = data

        return combined_result

    async def _fetch_single_binance_ohlcv(
        self,
        session: aiohttp.ClientSession,
        symbol: str,
        convert: str,
        interval: str,
        limit: int,
    ) -> Dict:
        """Helper to fetch OHLCV for a single symbol from Binance."""
        pair = f"{symbol}{convert}"
        try:
            async with session.get(
                f"{self.BINANCE_BASE_URL}/klines",
                params={
                    mc.KEY_SYMBOL: pair,
                    mc.KEY_INTERVAL: interval,
                    mc.KEY_LIMIT: limit,
                },
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                response.raise_for_status()
                data = await response.json()

                # Parse Binance kline data
                if data:
                    latest = data[-1]
                    return {
                        mc.KEY_OPEN_TIME: latest[0],
                        mc.KEY_OPEN: float(latest[1]),
                        mc.KEY_HIGH: float(latest[2]),
                        mc.KEY_LOW: float(latest[3]),
                        mc.KEY_CLOSE: float(latest[4]),
                        mc.KEY_VOLUME: float(latest[5]),
                        mc.KEY_CLOSE_TIME: latest[6],
                        mc.KEY_QUOTE_ASSET_VOLUME: float(latest[7]),
                        mc.KEY_NUMBER_OF_TRADES: latest[8],
                    }
                return {mc.KEY_ERROR: "No data returned from Binance"}
        except aiohttp.ClientError as e:
            return {mc.KEY_ERROR: f"Binance API error: {str(e)}"}
        except Exception as e:
            return {mc.KEY_ERROR: f"Unexpected error: {str(e)}"}
