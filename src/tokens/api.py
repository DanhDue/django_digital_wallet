from typing import List

from ninja import Router

import helpers
from helpers.base_response_schema import BaseResponseSchema
from tokens.schemas import TokenSchema

router = Router(tags=["Tokens"])


@router.get(
    "",
    response=BaseResponseSchema[List[TokenSchema]],
    auth=helpers.api_auth_user_or_anon,
)
def retrieve_transaction_list(request):
    pass
