from typing import List

from ninja import Router

import helpers

from helpers.base_response_schema import BaseResponseSchema
from transactions.schemas import TransactionSchema

router = Router(tags=["Transactions"])


@router.get(
    "",
    response=BaseResponseSchema[List[TransactionSchema]],
    auth=helpers.api_auth_user_or_anon,
)
def retrieve_transaction_list(request):
    pass
