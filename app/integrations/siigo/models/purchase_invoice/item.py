from pydantic import BaseModel

from app.integrations.siigo.models.purchase_invoice.tax import (
    PurchaseInvoiceTax,
)


class PurchaseInvoiceItem(BaseModel):
    code: str
    description: str | None = None

    quantity: float
    price: float

    discount: float | None = None

    taxes: list[PurchaseInvoiceTax] = []