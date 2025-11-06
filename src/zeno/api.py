import os
from typing import Optional

os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

from ninja_extra import NinjaExtraAPI
from ninja_jwt.controller import NinjaJWTDefaultController

api = NinjaExtraAPI()
api.register_controllers(NinjaJWTDefaultController)
api.add_router("/wallets", "wallets.api.router")
api.add_router("/transactions", "transactions.api.router")
api.add_router("/tokens", "tokens.api.router")
api.add_router("/markets", "markets.api.router")
