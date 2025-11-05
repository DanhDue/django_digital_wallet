from typing import List

from django.shortcuts import get_object_or_404
from ninja import Router

import helpers
from services.solana_service import SolanaService

import json

from .models import WalletModel
from .schemas import WalletModelCreationSchema, WalletModelSchema

router = Router()


@router.get("", response=List[WalletModelSchema], auth=helpers.api_auth_user_required)
def retrieve_wallet_list(request):
    qs = WalletModel.objects.filter(user=request.user)
    return qs


@router.post("", response=WalletModelSchema, auth=helpers.api_auth_user_or_anon)
def create_wallet(request, data: WalletModelCreationSchema):
    obj = WalletModel(**data.dict())
    if request.user.is_authenticated:
        obj.user = request.user
    obj.save()
    return obj


@router.get("/{address}")
async def wallet_balance(request, address: str):
    """Async endpoint to fetch SOL balance."""
    balance = await SolanaService.get_balance(address)
    wallet = await SolanaService.create_or_restore_wallet()
    return {"address": address, "balance_SOL": balance, "wallet": wallet}


@router.get("/tokens/{address}", auth=helpers.api_auth_user_or_anon)
async def wallet_tokens(request, address: str):
    """Async endpoint to fetch token accounts."""
    tokens = await SolanaService.get_token_accounts(address)
    return {"address": address, "tokens": tokens}
