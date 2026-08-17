from pydantic import BaseModel
from typing import Optional


class CheckPaymentSchema(BaseModel):
    slug: str


class TransactionSchema(BaseModel):
    payment_id: Optional[str]
    webapp_id: Optional[str]