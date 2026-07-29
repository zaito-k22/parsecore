from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class InvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int

    invoice_number: str | None
    supplier_name: str |None
    supplier_nit: str | None

    issue_date: str | None

    subtotal: float | None
    tax: float | None
    total: float | None

    original_filename: str

    drive_file_id: str | None
    drive_folder: str | None

    status: str

    created_at: datetime


class InvoiceListResponse(BaseModel):
    invoices: list[InvoiceResponse]


class InvoiceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str | None = Field(
        default=None,
        description="Nuevo estado de la factura.",
    )

    drive_file_id: str | None = Field(
        default=None,
        description="ID del archivo en Google Drive.",
    )

    drive_folder: str | None = Field(
        default=None,
        description="Carpeta de Google Drive.",
    )