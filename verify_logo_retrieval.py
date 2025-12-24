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
        # Test 1: With metadata (include_metadata=True) - First run (cached)
        print("Test 1: Fetching with full metadata (include_metadata=True)...")
        start_time = time.time()
        result_with_metadata = await service.get_cryptocurrency_listings_latest(
            limit=5, include_metadata=True
        )
        end_time = time.time()
        print(f"Time taken: {end_time - start_time:.4f}s")

        for crypto in result_with_metadata:
            print(f"\n--- {crypto.get('name')} ({crypto.get('symbol')}) ---")
            print(f"Logo: {crypto.get('logo')}")
            print(f"Description: {str(crypto.get('description'))[:100]}...")
            urls = crypto.get("urls", {})
            website = urls.get("website", [None])[0] if urls else None
            print(f"Website: {website}")

        # Test 2: Without metadata (include_metadata=False)
        print("\nTest 2: Fetching without metadata (include_metadata=False)...")
        result_no_metadata = await service.get_cryptocurrency_listings_latest(
            limit=5, include_metadata=False
        )
        for crypto in result_no_metadata:
            print(
                f"Crypto: {crypto.get('name')} ({crypto.get('symbol')}) - Logo: {crypto.get('logo')} - Desc: {crypto.get('description')}"
            )

    except Exception as e:
        print(f"Error during verification: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(verify())
