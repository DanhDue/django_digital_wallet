from typing import List

from ninja import Router

import helpers
from schemas.base_response_schema import BaseResponseSchema
from schemas.wallet_schemas import WalletModelCreationSchema, WalletModelSchema
from services.solana_service import SolanaService

from .models import WalletModel

router = Router(tags=["Wallets"])


@router.get(
    "",
    response=BaseResponseSchema[List[WalletModelSchema]],
    auth=helpers.api_auth_user_required,
    summary="Retrieve all wallets by user",
    description="Fetch a list of all wallet instances associated with the authenticated user.",
)
def retrieve_wallet_list(request):
    print(f"create_wallet: userID: ${request.user}")
    qs = WalletModel.objects.filter(user=request.user)
    return BaseResponseSchema[List[WalletModelSchema]](
        data=qs, message="fetch wallet list successfully"
    )


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
    wallet = await SolanaService.create_or_restore_wallet(data)
    return BaseResponseSchema[WalletModelSchema](
        data=wallet,
        message="fetch wallet info successfully",
    ).to_dict()


@router.get(
    "/{address}",
    response=BaseResponseSchema[WalletModelSchema],
    summary="Validate a wallet by its address.",
    description="Validate and retrieve wallet information (including SOL balance) by providing the wallet address.",
)
async def wallet_validation(request, address: str):
    print(f"create_wallet: userID: ${request.user.id}")
    is_valid = await SolanaService.validate_public_key()
    balance = await SolanaService.get_balance(address)
    return BaseResponseSchema[WalletModelSchema](
        data=WalletModelSchema(address, isValid=is_valid, balance=balance),
        message="fetch wallet info successfully",
    )
