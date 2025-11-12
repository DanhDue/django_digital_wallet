import os

os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

from ninja_extra import NinjaExtraAPI
from ninja_jwt.controller import NinjaJWTDefaultController
from django.urls import path

from wallets.api import router as wallets_router, wallet_router_pre_release
from transactions.api import router as transactions_router
from tokens.api import router as tokens_router, token_router_pre_release
from markets.api import router as markets_router

api_pre_release = NinjaExtraAPI(version="0.0.1")
api_pre_release.register_controllers(NinjaJWTDefaultController)

api_pre_release.add_router("/wallets", wallet_router_pre_release)
api_pre_release.add_router("/tokens", token_router_pre_release)

api_v1 = NinjaExtraAPI(version="1.0.0")
api_v1.register_controllers(NinjaJWTDefaultController)

api_v1.add_router("/wallets", wallets_router)
api_v1.add_router("/transactions", transactions_router)
api_v1.add_router("/tokens", tokens_router)
api_v1.add_router("/markets", markets_router)
