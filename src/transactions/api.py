from typing import List, Optional

from ninja import Query
from ninja_extra import Router

import helpers

from schemas.base_response_schema import BaseResponseSchema
from schemas.transaction_schemas import TransactionRetrieverSchema

from services.solana_service import SolanaService

router = Router(tags=["Transactions"])

solana_service = SolanaService()


@router.get(
    "",
    response=dict,
    auth=helpers.api_auth_user_or_anon,
)
async def retrieve_transaction_list(request, owner: str, limit: int):
    print(f"retrieve_transaction_list(request, account: {owner}, limit: {limit})")
    result = await solana_service.fetch_transactions_by_owner(
        data=TransactionRetrieverSchema(account=owner, limit=limit)
    )
    return BaseResponseSchema(
        data=result,
    ).to_dict()


@router.get(
    "/{signature}",
    response=dict,
    auth=helpers.api_auth_user_or_anon,
)
async def retrieve_transaction(
    request,
    signature: str,
    owners: Optional[List[str]] = Query(None),
    parsed_json: bool = False,
):
    print(f"retrieve_transaction(request, signature: {signature})")
    result = await solana_service.fetch_transactions(
        signature=signature, owner=owners, parsed_json=parsed_json
    )
    return BaseResponseSchema(
        data=result,
    ).to_dict()
