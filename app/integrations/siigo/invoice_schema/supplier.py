from pydantic import BaseModel


class Supplier(BaseModel):
    identification: str
    name: str | None = None