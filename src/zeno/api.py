from typing import Optional

from ninja import Schema
from ninja_extra import NinjaExtraAPI
from ninja_jwt.authentication import JWTAuth
from ninja_jwt.controller import NinjaJWTDefaultController
import helpers

api = NinjaExtraAPI()
api.register_controllers(NinjaJWTDefaultController)
api.add_router("/wallets", "wallets.api.router")


class UserSchema(Schema):
    username: str
    email: Optional[str] = None
    is_authenticated: bool


@api.get(
    "/me",
    response=UserSchema,
    auth=helpers.api_auth_user_required,
)
def me(request):
    return request.user
