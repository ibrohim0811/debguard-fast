from pydantic import BaseModel


class CheckPaymentSchema(BaseModel):
    slug: str