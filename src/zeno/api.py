import os

from ninja_extra import Router
from schemas.base_response_schema import BaseResponseSchema

os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

from ninja_extra import NinjaExtraAPI
from ninja_jwt.controller import NinjaJWTDefaultController
from django.urls import path

from wallets.api import router as wallets_router, wallet_router_pre_release
from transactions.api import router as transactions_router
from tokens.api import router as tokens_router, token_router_pre_release
from markets.api import router as markets_router
from accounts.api import get_users_router
from d3votion.api import router as d3votion_router

health_check_api = NinjaExtraAPI(
    title="Zeno",
    version="0.0.1",
    description="Health Check API for the Zeno service.",
    app_name="Zeno Health Check",
)

health_check_router = Router(tags=["Healthz"])


@health_check_router.get("")
def healthz(request):
    return BaseResponseSchema(message="Your service is live 🎉").to_dict()


health_check_api.add_router("", health_check_router)


api_pre_release = NinjaExtraAPI(
    title="Zeno",
    version="0.0.2",
    description="Pre-release API for the Zeno service.",
    app_name="Zeno Pre-release",
)

api_pre_release.add_router("/wallets", wallet_router_pre_release)
api_pre_release.add_router("/tokens", token_router_pre_release)
api_pre_release.add_router("/users", get_users_router())

api_v1 = NinjaExtraAPI(
    title="Zeno", version="1.0.0", description="The Zeno APIs service.", app_name="Zeno"
)

api_v1.add_router("/wallets", wallets_router)
api_v1.add_router("/transactions", transactions_router)
api_v1.add_router("/tokens", tokens_router)
api_v1.add_router("/markets", markets_router)
api_v1.add_router("/users", get_users_router())
api_v1.add_router("/d3votion", d3votion_router)
