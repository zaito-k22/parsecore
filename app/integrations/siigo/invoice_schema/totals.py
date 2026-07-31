from pydantic import BaseModel


class InvoiceTotals(BaseModel):
    subtotal: float

    tax: float

    total: float