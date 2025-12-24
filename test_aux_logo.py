import asyncio
import os
import sys

SRC_PATH = os.path.abspath(os.path.join(os.getcwd(), "src"))
sys.path.append(SRC_PATH)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "zeno.settings")
import django
django.setup()

from services.coinmarketcap_service import CoinMarketCapService
from services import market_constants as mc

async def main():
    service = CoinMarketCapService()
    params = {
        mc.KEY_START: 1,
        mc.KEY_LIMIT: 5,
        mc.KEY_CONVERT: "USD",
        "aux": "logo"
    }
    print("Testing aux=logo...")
    response = await service._make_request("cryptocurrency/listings/latest", params)
    data = response.get(mc.KEY_DATA, [])
    if data:
        for item in data:
            print(f"- {item.get(mc.KEY_SYMBOL)}: logo={item.get(mc.KEY_LOGO)}")
    else:
        print("No data or error:", response.get(mc.KEY_ERROR))

if __name__ == "__main__":
    asyncio.run(main())
