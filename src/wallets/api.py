from typing import List

from django.shortcuts import get_object_or_404
from ninja import Router

import helpers

from .models import WalletModel
from .schemas import WalletModelCreationSchema, WalletModelSchema

router = Router()


@router.get("", response=List[WalletModelSchema], auth=helpers.api_auth_user_required)
def retrieve_wallet_list(request):
    qs = WalletModel.objects.filter(user=request.user)
    return qs


@router.get("/{id}", response=WalletModelSchema, auth=helpers.api_auth_user_required)
def retrieve_wallet(request, id: int):
    obj = get_object_or_404(
        WalletModel,
        id=id,
        user=request.user,
    )
    return obj


@router.post("", response=WalletModelSchema, auth=helpers.api_auth_user_or_anon)
def create_wallet(request, data: WalletModelCreationSchema):
    obj = WalletModel(**data.dict())
    if request.user.is_authenticated:
        obj.user = request.user
    obj.save()
    return obj
