from pydantic import BaseModel

from app.integrations.siigo.models.purchase_invoice.document import (
    PurchaseInvoiceDocument,
)
from app.integrations.siigo.models.purchase_invoice.item import (
    PurchaseInvoiceItem,
)
from app.integrations.siigo.models.purchase_invoice.payment import (
    PurchaseInvoicePayment,
)
from app.integrations.siigo.models.purchase_invoice.supplier import (
    PurchaseInvoiceSupplier,
)


class PurchaseInvoiceRequest(BaseModel):
    document: PurchaseInvoiceDocument

    supplier: PurchaseInvoiceSupplier

    date: str

    observations: str | None = None

    items: list[PurchaseInvoiceItem]

    payments: list[PurchaseInvoicePayment]