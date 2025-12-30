from django.contrib.auth.models import User
from ninja_extra import Router

from ninja_jwt.routers.obtain import (
    obtain_token,
    refresh_token,
    schema as obtain_schema,
)
from ninja_jwt.routers.verify import verify_token, schema as verify_schema

import helpers
from schemas.base_response_schema import BaseResponseSchema
from .schemas import RegisterSchema, AccountSchema


def register(request, data: RegisterSchema):
    try:
        if User.objects.filter(username=data.username).exists():
            return BaseResponseSchema(
                success=False, message="Username already exists"
            ).to_dict()

        user = User.objects.create_user(
            username=data.username, password=data.password, email=data.email
        )

        account_data = AccountSchema.from_orm(user)
        return BaseResponseSchema[AccountSchema](
            data=account_data, message="User registered successfully"
        ).to_dict()
    except Exception as e:
        return BaseResponseSchema(success=False, message=str(e)).to_dict()


def me(request):
    account_data = AccountSchema.from_orm(request.user)
    return BaseResponseSchema[AccountSchema](
        data=account_data, message="User profile fetched successfully"
    ).to_dict()


def get_users_router():
    router = Router(tags=["Users"])

    # Consolidation: Add JWT routes directly
    router.post(
        "/login",
        response=obtain_schema.obtain_pair_schema.get_response_schema(),
        auth=None,
    )(obtain_token)
    router.post(
        "/refresh",
        response=obtain_schema.obtain_pair_refresh_schema.get_response_schema(),
        auth=None,
    )(refresh_token)
    router.post(
        "/verify",
        response={200: verify_schema.verify_schema.get_response_schema()},
        auth=None,
    )(verify_token)

    # Add user routes
    router.post("/register", response=dict, auth=None)(register)
    router.get("/me", response=dict, auth=helpers.api_auth_user_required)(me)

    return router
