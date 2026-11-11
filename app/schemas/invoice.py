from datetime import datetime

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from app.core.invoice_status import normalize_status


class InvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int

    invoice_number: str | None
    supplier_name: str | None
    supplier_nit: str | None = Field(
        validation_alias=AliasChoices("supplier_nit", "tax_id"),
    )

    issue_date: str | None = Field(
        validation_alias=AliasChoices("display_issue_date", "issue_date"),
    )

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

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str | None) -> str | None:
        if value is None:
            return None

        return normalize_status(value)
