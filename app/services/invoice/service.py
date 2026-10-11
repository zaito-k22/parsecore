import asyncio
import json
import logging
import os
import tempfile
import time

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.exceptions.invoice import InvoiceNotFound
from app.models.invoice import Invoice
from app.repositories.invoice_repository import InvoiceRepository
from app.services.llm.service import llm_service
from app.services.normalization.service import to_invoice_fields
from app.services.ocr.service import ocr_service

logger = logging.getLogger(__name__)


class InvoiceService:

    def __init__(self, db: Session):
        self.repository = InvoiceRepository(db)

    def _extract(self, path: str) -> tuple[dict, int]:
        """
        OCR + LLM. Es código síncrono y pesado: se ejecuta en un hilo
        (ver process) para no bloquear el event loop de FastAPI.
        """

        ocr_result = ocr_service.extract_text(path)

        text = ocr_result["text"]

        logger.info(
            "OCR listo: %s páginas, %s caracteres",
            ocr_result.get("pages"),
            len(text),
        )

        document = llm_service.extract_document(text)

        return document, len(text)

    async def process(self, file: UploadFile):

        filename = file.filename or "unnamed"

        suffix = os.path.splitext(filename)[1]

        content = await file.read()

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
        ) as temp_file:

            temp_file.write(content)

            temp_path = temp_file.name

        try:

            started = time.perf_counter()

            document, _ = await asyncio.to_thread(
                self._extract,
                temp_path,
            )

            logger.info(
                "Extracción completada en %.1fs (%s)",
                time.perf_counter() - started,
                filename,
            )

            invoice = Invoice(
                **to_invoice_fields(document),
                original_filename=filename,
                drive_file_id=None,
                drive_folder=None,
                raw_json=json.dumps(
                    document,
                    ensure_ascii=False,
                ),
                status="processed",
            )

            invoice = self.repository.create(invoice)

            return {
                "success": True,
                "invoice_id": invoice.id,
                "filename": filename,
                "invoice": document,
            }

        finally:

            if os.path.exists(temp_path):
                os.remove(temp_path)

    def get(
        self,
        invoice_id: int,
    ):

        invoice = self.repository.get_by_id(invoice_id)

        if invoice is None:
            raise InvoiceNotFound(invoice_id)

        return invoice

    def list(self):

        return self.repository.list()

    def update(
        self,
        invoice_id: int,
        status: str | None,
        drive_file_id: str | None,
        drive_folder: str | None,
    ):

        invoice = self.repository.get_by_id(invoice_id)

        if invoice is None:
            raise InvoiceNotFound(invoice_id)

        if status is not None:
            invoice.status = status

        if drive_file_id is not None:
            invoice.drive_file_id = drive_file_id

        if drive_folder is not None:
            invoice.drive_folder = drive_folder

        return self.repository.update(invoice)

    def delete(
        self,
        invoice_id: int,
    ):

        invoice = self.repository.get_by_id(invoice_id)

        if invoice is None:
            raise InvoiceNotFound(invoice_id)

        self.repository.delete(invoice)

        return True