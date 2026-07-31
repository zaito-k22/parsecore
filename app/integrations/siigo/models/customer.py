from pydantic import BaseModel


class SiigoCustomer(BaseModel):
    id: str
    identification: str
    person_type: str
    active: bool
    name: list[str]