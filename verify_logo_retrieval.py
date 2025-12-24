import os
import sys
import django
import asyncio
import time

# Set up Django environment
sys.path.append(os.path.join(os.getcwd(), "src"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "zeno.settings")
django.setup()

from services.coinmarketcap_service import CoinMarketCapService


async def verify():
    service = CoinMarketCapService()

    try:
        # Test 1: With logos (include_info=True) - First run (possibly cache miss)
        print("Test 1: Fetching with logos (include_info=True)...")
        start_time = time.time()
        result_with_logo = await service.get_cryptocurrency_listings_latest(
            limit=5, include_info=True
        )
        end_time = time.time()
        print(f"Time taken: {end_time - start_time:.4f}s")

        for crypto in result_with_logo:
            print(
                f"Crypto: {crypto.get('name')} ({crypto.get('symbol')}) - Logo: {crypto.get('logo')}"
            )

        # Test 2: Repeat to check cache (include_info=True)
        print("\nTest 2: Fetching again to check cache...")
        start_time = time.time()
        result_cached = await service.get_cryptocurrency_listings_latest(
            limit=5, include_info=True
        )
        end_time = time.time()
        print(f"Time taken (cache hit): {end_time - start_time:.4f}s")

        # Test 3: Without logos (include_info=False)
        print("\nTest 3: Fetching without logos (include_info=False)...")
        result_no_logo = await service.get_cryptocurrency_listings_latest(
            limit=5, include_info=False
        )
        for crypto in result_no_logo:
            print(
                f"Crypto: {crypto.get('name')} ({crypto.get('symbol')}) - Logo: {crypto.get('logo')}"
            )

    except Exception as e:
        print(f"Error during verification: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(verify())
