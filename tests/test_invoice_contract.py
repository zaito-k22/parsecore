from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models.invoice import Invoice
from app.schemas.invoice import InvoiceListResponse, InvoiceResponse, InvoiceUpdate


def _invoice() -> Invoice:
    return Invoice(
        id=7,
        invoice_number="F-001",
        supplier_name="Proveedor Sintético",
        tax_id="B30142516",
        issue_date=date(2024, 3, 15),
        issue_date_raw="15/03/2024",
        subtotal=Decimal("100.10"),
        tax=Decimal("19.02"),
        total=Decimal("119.12"),
        original_filename="synthetic.pdf",
        drive_file_id=None,
        drive_folder=None,
        raw_json="{}",
        status="done",
        created_at=datetime(2024, 3, 15, 10, 0, tzinfo=UTC),
        updated_at=datetime(2024, 3, 15, 10, 0, tzinfo=UTC),
    )


def test_legacy_invoice_response_structure():
    response = InvoiceResponse.model_validate(_invoice()).model_dump(mode="json")

    assert set(response) == {
        "id",
        "invoice_number",
        "supplier_name",
        "supplier_nit",
        "issue_date",
        "subtotal",
        "tax",
        "total",
        "original_filename",
        "drive_file_id",
        "drive_folder",
        "status",
        "created_at",
    }
    assert response["supplier_nit"] == "B30142516"
    assert response["issue_date"] == "2024-03-15"
    assert response["subtotal"] == 100.1
    assert response["total"] == 119.12


def test_legacy_list_response_structure():
    response = InvoiceListResponse(
        invoices=[InvoiceResponse.model_validate(_invoice())]
    ).model_dump(mode="json")

    assert set(response) == {"invoices"}
    assert len(response["invoices"]) == 1


def test_legacy_issue_date_raw_is_used_when_date_is_unknown():
    invoice = _invoice()
    invoice.issue_date = None

    response = InvoiceResponse.model_validate(invoice)

    assert response.issue_date == "15/03/2024"


def test_processed_status_is_mapped_to_done():
    body = InvoiceUpdate(status="processed")

    assert body.status == "done"


def test_invalid_status_is_rejected():
    with pytest.raises(ValidationError):
        InvoiceUpdate(status="cualquier-cosa")
