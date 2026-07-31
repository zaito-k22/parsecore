from pydantic import BaseModel


class PurchaseInvoicePayment(BaseModel):
    id: int

    value: float

    due_date: str | None = None