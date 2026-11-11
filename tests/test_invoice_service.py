import asyncio
import hashlib
from copy import deepcopy
from datetime import UTC, date, datetime
from decimal import Decimal
from io import BytesIO

import pytest
from sqlalchemy import select
from starlette.datastructures import UploadFile

from app.core.tenants import DEFAULT_TENANT_ID
from app.exceptions.invoice import InvoiceNotFound
from app.models.audit_event import AuditEvent
from app.models.extraction import Extraction
from app.models.invoice import Invoice
from app.services.invoice.service import InvoiceService
from app.services.storage.local import LocalStorageBackend

pytestmark = pytest.mark.db


class FakeOCR:
    engine = "fake-ocr"

    def __init__(self):
        self.calls = 0

    def extract_text(self, path):
        self.calls += 1
        return {
            "text": "Proveedor Sintético\nTotal 119,12",
            "lines": ["Proveedor Sintético", "Total 119,12"],
            "line_confidences": [0.99, 0.95],
            "pages": 1,
        }


class FakeLLM:
    model = "fake-llm"

    def __init__(self, document):
        self.document = document
        self.calls = 0

    def extract_document(self, text):
        self.calls += 1
        return deepcopy(self.document)


def _document():
    return {
        "supplier": {
            "name": "Proveedor Sintético",
            "tax_id": "B30142516",
            "country": "ES",
        },
        "invoice": {
            "number": "F-001",
            "date": "15/03/2024",
            "currency": "EUR",
        },
        "amounts": {
            "subtotal": "100,10",
            "tax_total": "19,02",
            "total": "119,12",
        },
        "warnings": [],
    }


def _upload(content: bytes, filename: str = "synthetic.pdf") -> UploadFile:
    return UploadFile(file=BytesIO(content), filename=filename)


def _process(service: InvoiceService, content: bytes, filename: str = "synthetic.pdf"):
    return asyncio.run(service.process(_upload(content, filename)))


def _service(db_session, tmp_path, document=None):
    ocr = FakeOCR()
    llm = FakeLLM(document or _document())
    storage = LocalStorageBackend(tmp_path)
    service = InvoiceService(db_session, storage=storage, ocr=ocr, llm=llm)

    return service, ocr, llm, storage


def test_process_persists_invoice_extraction_and_decimal(db_session, tmp_path):
    service, _, _, _ = _service(db_session, tmp_path)
    content = b"%PDF-1.4 synthetic invoice"

    result = _process(service, content)

    assert result["duplicate"] is False
    assert result["invoice"] == _document()

    db_session.expire_all()
    invoice = db_session.get(Invoice, result["invoice_id"])

    assert invoice is not None
    assert invoice.public_id is not None
    assert invoice.tenant_id == DEFAULT_TENANT_ID
    assert invoice.sha256 == hashlib.sha256(content).hexdigest()
    assert invoice.storage_uri is not None
    assert invoice.storage_uri.startswith(str(DEFAULT_TENANT_ID))
    assert invoice.storage_uri.endswith(".pdf")

    assert invoice.supplier_name == "Proveedor Sintético"
    assert invoice.supplier_nit == "B30142516"
    assert invoice.tax_id_country == "ES"
    assert invoice.currency == "EUR"
    assert invoice.invoice_number == "F-001"
    assert invoice.issue_date == date(2024, 3, 15)
    assert invoice.issue_date_raw == "15/03/2024"
    assert invoice.subtotal == Decimal("100.10")
    assert invoice.tax == Decimal("19.02")
    assert invoice.total == Decimal("119.12")
    assert invoice.status == "done"
    assert invoice.deleted_at is None
    assert invoice.created_at is not None
    assert invoice.updated_at is not None

    from app.models.extraction import Extraction
    extraction = db_session.scalar(select(Extraction))

    assert extraction is not None
    assert extraction.invoice_id == invoice.id
    assert extraction.version == 1
    assert extraction.ocr_engine == "fake-ocr"
    assert extraction.llm_model == "fake-llm"
    assert extraction.ocr_text == "Proveedor Sintético\nTotal 119,12"
    assert extraction.ocr_lines == [
        {"text": "Proveedor Sintético", "confidence": 0.99},
        {"text": "Total 119,12", "confidence": 0.95},
    ]
    assert extraction.result == _document()
    assert extraction.warnings == []
    assert extraction.duration_ms >= 0


def test_process_deduplicates_by_tenant_and_does_not_reprocess(db_session, tmp_path):
    service, ocr, llm, _ = _service(db_session, tmp_path)
    content = b"%PDF-1.4 duplicate"

    first = _process(service, content, "first.pdf")
    second = _process(service, content, "second.pdf")

    assert second["duplicate"] is True
    assert second["invoice_id"] == first["invoice_id"]
    assert second["filename"] == "first.pdf"
    assert ocr.calls == 1
    assert llm.calls == 1

    assert db_session.scalar(select(Invoice).where(Invoice.id == first["invoice_id"]))
    assert db_session.query(Invoice).count() == 1

    events = db_session.query(AuditEvent).order_by(AuditEvent.id).all()

    assert len(events) >= 1

    duplicate_events = [e for e in events if e.action == "invoice.duplicate"]
    assert len(duplicate_events) == 1
    assert duplicate_events[0].invoice_id == first["invoice_id"]


def test_patch_records_audit_event(db_session, tmp_path):
    service, _, _, _ = _service(db_session, tmp_path)
    result = _process(service, b"%PDF-1.4 patch")

    invoice = service.update(
        result["invoice_id"],
        "needs_review",
        "drive-1",
        "invoices/2024",
    )

    assert invoice.status == "needs_review"
    assert invoice.drive_file_id == "drive-1"
    assert invoice.drive_folder == "invoices/2024"

    events = db_session.query(AuditEvent).order_by(AuditEvent.id.desc()).all()

    assert len(events) >= 2

    updated_event = events[0]

    assert updated_event.action == "invoice.updated"
    assert updated_event.tenant_id == DEFAULT_TENANT_ID
    assert updated_event.invoice_id == invoice.id
    assert updated_event.actor == "legacy-api"
    assert updated_event.diff["before"]["status"] == "done"
    assert updated_event.diff["after"]["status"] == "needs_review"
    assert updated_event.diff["after"]["drive_file_id"] == "drive-1"
    assert updated_event.diff["after"]["drive_folder"] == "invoices/2024"

    created_event = events[1]
    assert created_event.action in ("invoice.created", "invoice.processed")


def test_delete_is_soft_and_audited(db_session, tmp_path):
    service, _, _, _ = _service(db_session, tmp_path)
    result = _process(service, b"%PDF-1.4 delete")
    invoice_id = result["invoice_id"]

    assert service.delete(invoice_id) is True

    db_session.expire_all()
    invoice = db_session.get(Invoice, invoice_id)

    assert invoice is not None
    assert invoice.deleted_at is not None
    assert invoice.updated_at == invoice.deleted_at

    with pytest.raises(InvoiceNotFound):
        service.get(invoice_id)

    invoices, total = service.list()

    assert invoices == []
    assert total == 0

    events = db_session.query(AuditEvent).order_by(AuditEvent.id.desc()).all()

    assert len(events) >= 2

    deleted_event = events[0]

    assert deleted_event.action == "invoice.deleted"

    # Events ordenados por ID ascendente (más antiguos primero)
    events_asc = db_session.query(AuditEvent).order_by(AuditEvent.id).all()
    created_event = events_asc[0]
    processed_event = events_asc[1]

    assert processed_event.action == "invoice.processed"
    assert created_event.action == "invoice.created"
    assert deleted_event.action == "invoice.deleted"
    assert deleted_event.diff["before"] == {"deleted_at": None}
    assert deleted_event.diff["after"]["deleted_at"] == invoice.deleted_at.isoformat()


def test_list_filters_and_paginates(db_session):
    def invoice(
        number: str,
        supplier: str,
        tax_id: str,
        issue_date: date,
        status: str,
        deleted_at: datetime | None = None,
    ) -> Invoice:
        return Invoice(
            invoice_number=number,
            supplier_name=supplier,
            tax_id=tax_id,
            issue_date=issue_date,
            issue_date_raw=issue_date.isoformat(),
            subtotal=Decimal("10.00"),
            tax=Decimal("1.90"),
            total=Decimal("11.90"),
            original_filename=f"{number}.pdf",
            raw_json="{}",
            status=status,
            deleted_at=deleted_at,
        )

    db_session.add_all(
        [
            invoice("F-1", "Acme", "A-1", date(2024, 1, 10), "done"),
            invoice("F-2", "Beta", "B-2", date(2024, 2, 10), "needs_review"),
            invoice("F-3", "Acme", "A-1", date(2023, 12, 1), "done"),
            invoice(
                "F-4",
                "Acme",
                "A-1",
                date(2024, 3, 10),
                "done",
                deleted_at=datetime.now(UTC),
            ),
        ]
    )
    db_session.commit()

    service = InvoiceService(
        db_session,
        storage=LocalStorageBackend("/tmp/unused"),
        ocr=FakeOCR(),
        llm=FakeLLM({}),
    )

    invoices, total = service.list(status="done", page_size=1)
    assert total == 2
    assert len(invoices) == 1

    invoices, total = service.list(supplier="acme")
    assert total == 2

    invoices, total = service.list(tax_id="A-1")
    assert total == 2

    invoices, total = service.list(
        from_date=date(2024, 1, 1),
        to_date=date(2024, 12, 31),
    )
    assert total == 2

    invoices, total = service.list(page=2, page_size=2)
    assert total == 3
    assert len(invoices) == 1


def test_failed_extraction_marks_invoice_failed(db_session, tmp_path):
    class FailingLLM(FakeLLM):
        def extract_document(self, text):
            raise RuntimeError("synthetic failure")

    ocr = FakeOCR()
    storage = LocalStorageBackend(tmp_path)
    service = InvoiceService(
        db_session,
        storage=storage,
        ocr=ocr,
        llm=FailingLLM(_document()),
    )

    with pytest.raises(RuntimeError, match="synthetic failure"):
        _process(service, b"%PDF-1.4 failure")

    invoice = db_session.scalar(select(Invoice))

    assert invoice is not None
    assert invoice.status == "failed"
    assert invoice.storage_uri is not None
    assert db_session.scalar(select(Extraction)) is None


def test_process_records_audit_events(db_session, tmp_path):
    service, _, _, _ = _service(db_session, tmp_path)
    result = _process(service, b"%PDF-1.4 audit-test")

    assert result["success"] is True
    assert result["duplicate"] is False

    events = db_session.query(AuditEvent).order_by(AuditEvent.id).all()
    assert len(events) == 2

    assert events[0].action == "invoice.created"
    assert events[1].action == "invoice.processed"

    assert events[0].invoice_id == result["invoice_id"]
    assert events[1].invoice_id == result["invoice_id"]


def test_duplicate_records_audit_event(db_session, tmp_path):
    service, _, _, _ = _service(db_session, tmp_path)

    first = _process(service, b"%PDF-1.4 duplicate-audit")
    assert first["duplicate"] is False

    second = _process(service, b"%PDF-1.4 duplicate-audit")
    assert second["duplicate"] is True

    events = db_session.query(AuditEvent).order_by(AuditEvent.id).all()

    duplicate_events = [e for e in events if e.action == "invoice.duplicate"]
    assert len(duplicate_events) == 1
    assert duplicate_events[0].invoice_id == first["invoice_id"]