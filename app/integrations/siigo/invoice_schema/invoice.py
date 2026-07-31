from pydantic import BaseModel

from app.integrations.siigo.invoice_schema.item import InvoiceItem
from app.integrations.siigo.invoice_schema.supplier import Supplier
from app.integrations.siigo.invoice_schema.totals import InvoiceTotals


class Invoice(BaseModel):
    supplier: Supplier

    date: str

    number: str | None = None

    observations: str | None = None

    items: list[InvoiceItem]

    totals: InvoiceTotals