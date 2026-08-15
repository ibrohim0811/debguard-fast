from pydantic import BaseModel
from typing import Optional


class WebappCreateSchema(BaseModel):
    domain: str
    title: str