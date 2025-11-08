from typing import List

from ninja_extra import Router

import helpers
from schemas.base_response_schema import BaseResponseSchema
from schemas.token_schemas import TokenSchema
from services.solana_service import SolanaService

router = Router(tags=["Tokens"])

solana_service = SolanaService()


@router.post(
    "/mint",
    summary="Mint more SPL tokens.",
    description=("Mint more SPL tokens ~ issue additional shares(phát hành thêm)."),
)
async def mint_token(request, address: str):
    print("get_token_mint(request, address: {address})")
    pass


@router.post(
    "/mint/authority",
    summary="Set new mint authority.",
    description=("Set new mint authority."),
)
async def set_authority(request, address: str):
    print("get_token_mint(request, address: {address})")
    pass


@router.post(
    "/account",
    summary="Create a token account for a SPL token.",
    description=("Create a token account for a SPL token."),
)
async def create_token_account():
    print("")
    pass


@router.get(
    "/account",
    summary="Get the token account for a SPL token.",
    description=("Get the token account for a SPL token."),
)
async def get_token_account():
    print("")
    pass


@router.get(
    "/accounts",
    summary="Get all token accounts by owner.",
    description=("Get all token accounts by owner."),
)
async def get_all_token_accounts():
    print("")
    pass


@router.delete(
    "/account",
    summary="Delete the token account for a SPL token.",
    description=("Delete the token account for a SPL token."),
)
async def close_token_account():
    print("")
    pass


@router.get(
    "/transfer",
    summary="Transfer tokens to another wallet.",
    description=("Transfer tokens to another wallet."),
)
async def transfer_tokens():
    print("")
    pass


@router.post(
    "",
    response=BaseResponseSchema[List[TokenSchema]],
    auth=helpers.api_auth_user_or_anon,
    summary="Create a new SPL token.",
    description=("Create a new SPL token."),
)
async def create_token(request):
    pass


@router.get(
    "/{mint_address}",
    response=dict,
    auth=helpers.api_auth_user_or_anon,
    summary="Get information about mint token.",
    description=("Get information about mint token."),
)
async def get_mint_token(request, mint_address):
    print(f"get_mint_token(request, mint_address: {mint_address})")
    mint_token_info = await solana_service.get_mint_token(mint_address=mint_address)
    return BaseResponseSchema(
        data=mint_token_info,
        message="fetch mint token info successfully",
    ).to_dict()


@router.delete(
    "",
    response=BaseResponseSchema[List[TokenSchema]],
    auth=helpers.api_auth_user_or_anon,
    summary="Burn SPL tokens.",
    description=("Burn SPL tokens."),
)
async def burn_token(request):
    pass
