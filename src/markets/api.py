from typing import List

from ninja import Router

import helpers
from schemas.base_response_schema import BaseResponseSchema
from schemas.market_schemas import MarketSchema

router = Router(tags=["Markets"])


@router.get(
    "",
    response=BaseResponseSchema[List[MarketSchema]],
    auth=helpers.api_auth_user_or_anon,
)
def retrieve_transaction_list(request):
    pass
