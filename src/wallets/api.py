from typing import Any, List

from ninja_extra import Router

import helpers
from schemas.base_response_schema import BaseResponseSchema
from schemas.wallet_schemas import (
    WalletAirdropSchema,
    WalletModelCreationSchema,
    WalletModelSchema,
)
from services.solana_service import SolanaService

from .models import WalletModel

router = Router(tags=["Wallets"])

wallet_router_pre_release = Router(tags=["Wallets"])

solana_service = SolanaService()


@wallet_router_pre_release.post(
    "/airdrop",
    response=dict,
    auth=helpers.api_auth_user_or_anon,
    summary="Airdrop SOL to wallet",
    description="Request an airdrop of SOL tokens to a specific wallet address",
)
async def airdrop(request, data: WalletAirdropSchema):
    print(f"airdrop(request, data: {data.address} - {data.amount} SOL)")
    result = await solana_service.airdrop(address=data.address, amount=data.amount)
    return BaseResponseSchema[WalletModelSchema](
        data=result, message="airdrop successfully"
    ).to_dict()


@router.post(
    "/airdrop",
    response=dict,
    auth=helpers.api_auth_user_or_anon,
    summary="Airdrop SOL to wallet",
    description="Request an airdrop of SOL tokens to a specific wallet address",
)
async def airdrop(request, data: WalletAirdropSchema):
    print(f"airdrop(request, data: {data.address} - {data.amount} SOL)")
    result = await solana_service.airdrop(address=data.address, amount=data.amount)
    return BaseResponseSchema[WalletModelSchema](
        data=result, message="airdrop successfully"
    ).to_dict()


@wallet_router_pre_release.post(
    "",
    response=dict,
    auth=helpers.api_auth_user_or_anon,
    summary="Create or restore a wallet",
    description=(
        "Create a new wallet or restore an existing wallet for the user. "
        "Allows both authenticated and anonymous users to generate or recover a wallet."
    ),
)
async def create_wallet(request, data: WalletModelCreationSchema):
    wallet = await solana_service.create_or_restore_wallet(data)
    return BaseResponseSchema[WalletModelSchema](
        data=wallet,
        message="fetch wallet info successfully",
    ).to_dict()


@router.post(
    "",
    response=dict,
    auth=helpers.api_auth_user_or_anon,
    summary="Create or restore a wallet",
    description=(
        "Create a new wallet or restore an existing wallet for the user. "
        "Allows both authenticated and anonymous users to generate or recover a wallet."
    ),
)
async def create_wallet(request, data: WalletModelCreationSchema):
    wallet = await solana_service.create_or_restore_wallet(data)
    return BaseResponseSchema[WalletModelSchema](
        data=wallet,
        message="fetch wallet info successfully",
    ).to_dict()


@router.get(
    "",
    response=BaseResponseSchema[List[WalletModelSchema]],
    auth=helpers.api_auth_user_required,
    summary="Retrieve all wallets by user",
    description="Fetch a list of all wallet instances associated with the authenticated user.",
)
def retrieve_wallet_list(request):
    print(f"create_wallet: userID: {request.user}")
    qs = WalletModel.objects.filter(user=request.user)
    return BaseResponseSchema[List[WalletModelSchema]](
        data=qs, message="fetch wallet list successfully"
    )


@wallet_router_pre_release.get(
    "/{address}",
    response=dict,
    auth=helpers.api_auth_user_or_anon,
    summary="Validate a wallet by its address.",
    description="Validate and retrieve wallet information (including SOL balance) by providing the wallet address.",
)
async def wallet_validation(request, address: str):
    print(f"create_wallet: userID: {request.user.id}")
    is_valid = solana_service.validate_public_key(wallet_address=address)
    balance = await solana_service.get_balance(address)
    print("balance", balance)
    return BaseResponseSchema[WalletModelSchema](
        data=WalletModelSchema(address=address, isValid=is_valid, balance=balance),
        message="fetch wallet info successfully",
    ).to_dict()


@router.get(
    "/{address}",
    response=dict,
    auth=helpers.api_auth_user_or_anon,
    summary="Validate a wallet by its address.",
    description="Validate and retrieve wallet information (including SOL balance) by providing the wallet address.",
)
async def wallet_validation(request, address: str):
    print(f"create_wallet: userID: {request.user.id}")
    is_valid = solana_service.validate_public_key(wallet_address=address)
    balance = await solana_service.get_balance(address)
    print("balance", balance)
    return BaseResponseSchema[WalletModelSchema](
        data=WalletModelSchema(address=address, isValid=is_valid, balance=balance),
        message="fetch wallet info successfully",
    ).to_dict()
