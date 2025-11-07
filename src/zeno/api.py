import os

os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

from ninja_extra import NinjaExtraAPI
from ninja_jwt.controller import NinjaJWTDefaultController
from django.urls import path

from wallets.api import router as wallets_router
from transactions.api import router as transactions_router
from tokens.api import router as tokens_router
from markets.api import router as markets_router

api = NinjaExtraAPI(version="1.0.0")
api.register_controllers(NinjaJWTDefaultController)

api.add_router("/wallets", wallets_router)
api.add_router("/transactions", transactions_router)
api.add_router("/tokens", tokens_router)
api.add_router("/markets", markets_router)
