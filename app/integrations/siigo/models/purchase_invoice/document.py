from pydantic import BaseModel


class PurchaseInvoiceDocument(BaseModel):
    id: int