from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.invoice_status import normalize_status
from app.core.tenants import DEFAULT_TENANT_ID
from app.exceptions.invoice import InvoiceNotFound
from app.models.audit_event import AuditEvent
from app.models.extraction import Extraction
from app.models.invoice import Invoice
from app.repositories.invoice_repository import InvoiceRepository
from app.services.normalization.service import to_invoice_fields
from app.services.storage.backend import StorageBackend
from app.services.storage.local import LocalStorageBackend

logger = logging.getLogger(__name__)

OCR_ENGINE = "paddleocr"
PROMPT_VERSION = "invoice_prompt_v1"
AUDIT_ACTOR = "legacy-api"


class InvoiceService:

    def __init__(
        self,
        db: Session,
        *,
        storage: StorageBackend | None = None,
        ocr=None,
        llm=None,
        tenant_id: UUID = DEFAULT_TENANT_ID,
    ):
        self.repository = InvoiceRepository(db)
        self.tenant_id = tenant_id

        if storage is None:
            from app.core.config import settings

            storage = LocalStorageBackend(settings.storage_path)

        if ocr is None:
            from app.services.ocr.service import ocr_service

            ocr = ocr_service

        if llm is None:
            from app.services.llm.service import llm_service

            llm = llm_service

        self.storage = storage
        self.ocr = ocr
        self.llm = llm
        self.ocr_engine = getattr(ocr, "engine", OCR_ENGINE)
        self.llm_model = getattr(llm, "model", "unknown")

    def _extract(self, path: Path) -> tuple[dict, dict, int]:
        started = time.perf_counter()

        ocr_result = self.ocr.extract_text(str(path))
        text = ocr_result.get("text") or ""
        document = self.llm.extract_document(text)

        duration_ms = int((time.perf_counter() - started) * 1000)

        return document, ocr_result, duration_ms

    async def process(self, file: UploadFile) -> dict[str, Any]:
        filename = file.filename or "unnamed"
        extension = Path(filename).suffix
        content = await file.read()

        sha256 = hashlib.sha256(content).hexdigest()
        existing = self.repository.get_by_sha256(self.tenant_id, sha256)

        if existing is not None:
            return self._duplicate_response(existing)

        # === Etapa A: recepción y creación ===
        public_id = uuid4()
        storage_uri = self.storage.save(
            content,
            tenant_id=self.tenant_id,
            public_id=public_id,
            extension=extension,
        )

        invoice = Invoice(
            public_id=public_id,
            tenant_id=self.tenant_id,
            sha256=sha256,
            storage_uri=storage_uri,
            original_filename=filename,
            drive_file_id=None,
            drive_folder=None,
            raw_json="{}",
            status="processing",
        )
        invoice = self.repository.add(invoice)

        self.repository.add_audit_event(
            AuditEvent(
                tenant_id=self.tenant_id,
                invoice_id=invoice.id,
                actor=AUDIT_ACTOR,
                action="invoice.created",
                diff={
                    "after": {
                        "public_id": str(invoice.public_id),
                        "filename": filename,
                        "tenant_id": str(self.tenant_id),
                    }
                },
            )
        )

        self.repository.commit()

        try:
            # Etapa B: procesamiento externo (fuera de transacción larga)
            document, ocr_result, duration_ms = await asyncio.to_thread(
                self._extract,
                self.storage.path_for(storage_uri),
            )
        except Exception:
            # Etapa D: procesamiento fallido
            invoice.status = "failed"
            invoice.updated_at = self._now()
            # Confirmar estado y evento fallido en una misma transacción
            self.repository.add_audit_event(
                AuditEvent(
                    tenant_id=self.tenant_id,
                    invoice_id=invoice.id,
                    actor=AUDIT_ACTOR,
                    action="invoice.failed",
                    diff={"before": {"status": "processing"}},
                )
            )
            self.repository.commit()

            raise

        # Etapa C: finalización exitosa
        fields = to_invoice_fields(document)

        before = {
            "status": "processing",
            "supplier_name": None,
            "tax_id": None,
            "invoice_number": None,
        }

        for field, value in fields.items():
            setattr(invoice, field, value)

        invoice.raw_json = json.dumps(
            document,
            ensure_ascii=False,
            default=str,
        )
        invoice.status = "done"
        invoice.updated_at = self._now()

        extraction = Extraction(
            invoice_id=invoice.id,
            version=1,
            ocr_engine=self.ocr_engine,
            llm_model=self.llm_model,
            prompt_version=PROMPT_VERSION,
            ocr_text=ocr_result.get("text"),
            ocr_lines=self._ocr_lines(ocr_result),
            result=document,
            warnings=self._warnings(document),
            duration_ms=duration_ms,
        )

        after_status_info = {
            "status": "done",
            "supplier_name": invoice.supplier_name,
            "tax_id": invoice.tax_id,
            "invoice_number": invoice.invoice_number,
        }

        # Agregar extraction y actualizar factura en la misma transacción
        self.repository.add_extraction(extraction)
        # Actualizar campos de la factura en session
        self.repository.add(invoice)

        self.repository.add_audit_event(
            AuditEvent(
                tenant_id=self.tenant_id,
                invoice_id=invoice.id,
                actor=AUDIT_ACTOR,
                action="invoice.processed",
                diff={"before": before, "after": after_status_info},
            )
        )

        self.repository.commit()

        return {
            "success": True,
            "invoice_id": invoice.id,
            "filename": filename,
            "invoice": document,
            "duplicate": False,
        }

    def get(self, invoice_id: int) -> Invoice:
        invoice = self.repository.get_by_id(self.tenant_id, invoice_id)

        if invoice is None:
            raise InvoiceNotFound(invoice_id)

        return invoice

    def list(
        self,
        *,
        status: str | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        supplier: str | None = None,
        tax_id: str | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> tuple[list[Invoice], int]:
        return self.repository.list(
            self.tenant_id,
            status=status,
            from_date=from_date,
            to_date=to_date,
            supplier=supplier,
            tax_id=tax_id,
            page=page,
            page_size=page_size,
        )

    def update(
        self,
        invoice_id: int,
        status: str | None,
        drive_file_id: str | None,
        drive_folder: str | None,
    ) -> Invoice:
        invoice = self.get(invoice_id)

        before = {
            "status": invoice.status,
            "drive_file_id": invoice.drive_file_id,
            "drive_folder": invoice.drive_folder,
        }

        if status is not None:
            invoice.status = normalize_status(status)

        if drive_file_id is not None:
            invoice.drive_file_id = drive_file_id

        if drive_folder is not None:
            invoice.drive_folder = drive_folder

        after = {
            "status": invoice.status,
            "drive_file_id": invoice.drive_file_id,
            "drive_folder": invoice.drive_folder,
        }

        invoice.updated_at = self._now()

        self.repository.add_audit_event(
            AuditEvent(
                tenant_id=self.tenant_id,
                invoice_id=invoice.id,
                actor=AUDIT_ACTOR,
                action="invoice.updated",
                diff={"before": before, "after": after},
            )
        )

        self.repository.add(invoice)
        self.repository.commit()

        return invoice

    def delete(self, invoice_id: int) -> bool:
        invoice = self.get(invoice_id)
        deleted_at = self._now()

        before = {"deleted_at": None}
        invoice.deleted_at = deleted_at
        invoice.updated_at = deleted_at

        self.repository.add_audit_event(
            AuditEvent(
                tenant_id=self.tenant_id,
                invoice_id=invoice.id,
                actor=AUDIT_ACTOR,
                action="invoice.deleted",
                diff={
                    "before": before,
                    "after": {"deleted_at": deleted_at.isoformat()},
                },
            )
        )

        self.repository.add(invoice)
        self.repository.commit()

        return True

    def _duplicate_response(self, invoice: Invoice) -> dict[str, Any]:
        self.repository.add_audit_event(
            AuditEvent(
                tenant_id=self.tenant_id,
                invoice_id=invoice.id,
                actor=AUDIT_ACTOR,
                action="invoice.duplicate",
                diff={"before": None, "after": {"original_filename": invoice.original_filename}},
            )
        )

        self.repository.commit()

        try:
            document = json.loads(invoice.raw_json)
        except (TypeError, ValueError):
            document = {}

        return {
            "success": True,
            "invoice_id": invoice.id,
            "filename": invoice.original_filename,
            "invoice": document,
            "duplicate": True,
        }

    def _ocr_lines(self, ocr_result: dict) -> list[dict]:
        lines = ocr_result.get("lines") or []
        confidences = ocr_result.get("line_confidences") or []

        return [
            {"text": str(line), "confidence": self._confidence(confidence)}
            for line, confidence in zip(lines, confidences, strict=False)
        ]

    def _confidence(self, value) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _warnings(self, document: dict) -> list:
        warnings = document.get("warnings")

        return warnings if isinstance(warnings, list) else []

    def _now(self) -> datetime:
        return datetime.now(UTC)