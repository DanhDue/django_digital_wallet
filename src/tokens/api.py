from typing import Any, List

from ninja_extra import Router

import helpers
from schemas.base_response_schema import BaseResponseSchema
from schemas.token_schemas import (
    TokenSchema,
    TransferTokenCreationSchema,
    TokenAccountCreationSchema,
)
from services.solana_service import SolanaService

router = Router(tags=["Tokens"])

solana_service = SolanaService()


@router.post(
    "/mint",
    summary="Mint more SPL tokens.",
    description=("Mint more SPL tokens ~ issue additional shares(phát hành thêm)."),
)
async def mint_token(request, address: str):
    pass


@router.post(
    "/mint/authority",
    summary="Set new mint authority.",
    description=("Set new mint authority."),
)
async def set_authority(request, address: str):
    pass


@router.post(
    "/account",
    auth=helpers.api_auth_user_or_anon,
    response=dict,
    summary="Create a new token account for a SPL token.",
    description=("Create a new token account for a SPL token."),
)
async def create_token_account(request, data: TokenAccountCreationSchema):
    result = await solana_service.create_token_account(data=data)
    return BaseResponseSchema(
        data=result, message="Create a new SPL token account successfully."
    ).to_dict()


@router.get(
    "/account",
    summary="Get the token account for a SPL token.",
    description=("Get the token account for a SPL token."),
)
async def get_token_account():
    pass


@router.get(
    "/accounts/{owner_address}",
    auth=helpers.api_auth_user_or_anon,
    response=dict,
    summary="Get all token accounts by owner.",
    description=("Get all token accounts by owner."),
)
async def get_all_token_accounts(request, owner_address):
    result = await solana_service.retrieve_token_accounts(owner_address)
    return BaseResponseSchema(
        data=result, message="Get token accounts successfully."
    ).to_dict()


@router.delete(
    "/account",
    summary="Delete the token account for a SPL token.",
    description=("Delete the token account for a SPL token."),
)
async def close_token_account():
    pass


@router.post(
    "/transfer",
    response=dict,
    auth=helpers.api_auth_user_or_anon,
    summary="Transfer tokens to another wallet.",
    description=("Transfer tokens to another wallet."),
)
async def transfer_tokens(request, data: TransferTokenCreationSchema):
    mint_address = (data.mint_address or "").strip()
    message = (
        "Prepare tokens transfering successfully."
        if data.is_preview
        else "Transfer tokens successfully."
    )

    service_methods = {
        # (has_mint_address, is_preview)
        (True, True): solana_service.prepare_to_transfer_spl_tokens,
        (True, False): solana_service.send_tokens,
        (False, True): solana_service.prepare_to_transfer_sol,
        (False, False): solana_service.send_sol,
    }

    has_mint_address = bool(mint_address)
    service_method = service_methods[(has_mint_address, data.is_preview)]
    result = await service_method(data=data)

    return BaseResponseSchema[Any](data=result, message=message).to_dict()


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
    mint_token_info = await solana_service.get_mint_token(mint_address=mint_address)
    return BaseResponseSchema[Any](
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
