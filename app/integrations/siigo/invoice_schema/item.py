from pydantic import BaseModel


class InvoiceItem(BaseModel):
    description: str

    quantity: float

    unit_price: float

    tax_percentage: float | None = None

    discount: float | None = None