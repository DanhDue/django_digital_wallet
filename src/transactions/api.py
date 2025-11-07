from typing import List

from ninja import Router

import helpers

from schemas.base_response_schema import BaseResponseSchema
from schemas.transaction_schemas import TransactionSchema

router = Router(tags=["Transactions"])


@router.get(
    "",
    response=BaseResponseSchema[List[TransactionSchema]],
    auth=helpers.api_auth_user_or_anon,
)
def retrieve_transaction_list(request):
    pass
