from typing import List

from ninja_extra import Router
from ninja import Query

import helpers
from schemas.base_response_schema import BaseResponseSchema
from schemas.market_schemas import (
    MarketSchema,
    CryptocurrencyListingsRequestSchema,
    CryptocurrencyInfoRequestSchema,
    CryptocurrencyInfoRequestSchema,
    PriceConversionRequestSchema,
    GlobalMetricsRequestSchema,
    CryptocurrencyMapRequestSchema,
    CryptocurrencySearchRequestSchema,
    CryptocurrencyOHLCVRequestSchema,
)
from services.coinmarketcap_service import CoinMarketCapService

router = Router(tags=["Markets"])
coinmarketcap_service = CoinMarketCapService()


@router.get(
    "",
    response=dict,
    auth=helpers.api_auth_user_or_anon,
)
async def retrieve_market_currencies(
    request, params: CryptocurrencyListingsRequestSchema = Query(...)
):
    """Get a paginated list of all active cryptocurrencies with latest market data."""
    result = await coinmarketcap_service.get_cryptocurrency_listings_latest(
        start=params.start,
        limit=params.limit,
        convert=params.convert,
        sort=params.sort,
        sort_dir=params.sort_dir,
        include_info=params.include_info,
    )
    return BaseResponseSchema(data=result).to_dict()


@router.get(
    "/info",
    response=dict,
    auth=helpers.api_auth_user_or_anon,
)
async def retrieve_cryptocurrency_info(
    request, params: CryptocurrencyInfoRequestSchema = Query(...)
):
    """Get comprehensive cryptocurrency data including quotes and metadata."""
    symbols = params.symbols.split(",") if params.symbols else None
    ids = [int(id) for id in params.ids.split(",")] if params.ids else None

    result = await coinmarketcap_service.get_cryptocurrency_details(
        symbols=symbols,
        ids=ids,
        convert=params.convert,
    )
    return BaseResponseSchema(data=result).to_dict()


@router.get(
    "/price",
    response=dict,
    auth=helpers.api_auth_user_or_anon,
)
async def convert_price(request, params: PriceConversionRequestSchema = Query(...)):
    """Convert an amount of one cryptocurrency to another currency."""
    result = await coinmarketcap_service.get_price_conversion(
        amount=params.amount,
        symbol=params.symbol,
        id=params.id,
        convert=params.convert,
    )
    return BaseResponseSchema(data=result).to_dict()


@router.get(
    "/metrics",
    response=dict,
    auth=helpers.api_auth_user_or_anon,
)
async def retrieve_global_metrics(
    request, params: GlobalMetricsRequestSchema = Query(...)
):
    """Get the latest global cryptocurrency market metrics."""
    result = await coinmarketcap_service.get_global_metrics_latest(
        convert=params.convert
    )
    return BaseResponseSchema(data=result).to_dict()


@router.get(
    "/maps",
    response=dict,
    auth=helpers.api_auth_user_or_anon,
)
async def retrieve_cryptocurrency_map(
    request, params: CryptocurrencyMapRequestSchema = Query(...)
):
    """Get a mapping of all cryptocurrencies to unique CoinMarketCap IDs."""
    result = await coinmarketcap_service.get_cryptocurrency_map(
        listing_status=params.listing_status,
        start=params.start,
        limit=params.limit,
    )
    return BaseResponseSchema(data=result).to_dict()


@router.get(
    "/search",
    response=dict,
    auth=helpers.api_auth_user_or_anon,
)
async def search_cryptocurrency(
    request, params: CryptocurrencySearchRequestSchema = Query(...)
):
    """Search for cryptocurrencies by name or symbol."""
    result = await coinmarketcap_service.search_cryptocurrency(
        query=params.query,
        limit=params.limit,
    )
    return BaseResponseSchema(data=result).to_dict()


@router.get(
    "/ohlcv",
    response=dict,
    auth=helpers.api_auth_user_or_anon,
)
async def retrieve_cryptocurrency_ohlcv(
    request, params: CryptocurrencyOHLCVRequestSchema = Query(...)
):
    """
    Get the latest OHLCV (Open, High, Low, Close, Volume) data from Binance.

    The 'convert' parameter specifies the quote currency for trading pairs.
    Supported values: USDT (default), BTC, BUSD, BNB, ETH, and other Binance-supported quote assets.
    Example: symbols=BTC,ETH with convert=USDT will fetch BTCUSDT and ETHUSDT pairs.
    """
    symbols = params.symbols.split(",") if params.symbols else None

    if not symbols:
        return BaseResponseSchema(
            error="Symbols are required for Binance OHLCV data"
        ).to_dict()

    result = await coinmarketcap_service.get_binance_ohlcv_latest(
        symbols=symbols,
        convert=params.convert,
    )
    return BaseResponseSchema(data=result).to_dict()
