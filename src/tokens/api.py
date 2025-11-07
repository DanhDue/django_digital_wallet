from typing import List

from ninja import Router

import helpers
from schemas.base_response_schema import BaseResponseSchema
from schemas.token_schemas import TokenSchema

router = Router(tags=["Tokens"])


@router.get(
    "",
    response=BaseResponseSchema[List[TokenSchema]],
    auth=helpers.api_auth_user_or_anon,
)
def retrieve_transaction_list(request):
    pass
