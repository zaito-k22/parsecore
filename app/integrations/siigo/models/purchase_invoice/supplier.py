from pydantic import BaseModel


class PurchaseInvoiceSupplier(BaseModel):
    identification: str
    branch_office: int = 0