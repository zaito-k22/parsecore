import json
import os
import tempfile

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.models.invoice import Invoice
from app.repositories.invoice_repository import InvoiceRepository
from app.services.llm.service import llm_service
from app.services.ocr.service import ocr_service


class InvoiceService:

    def __init__(self, db: Session):
        self.repository = InvoiceRepository(db)

    @staticmethod
    def _to_float(value):

        if value in (None, ""):
            return None

        if isinstance(value, (int, float)):
            return float(value)

        value = (
            str(value)
            .replace(".", "")
            .replace(",", ".")
        )

        try:
            return float(value)
        except ValueError:
            return None

    async def process(self, file: UploadFile):

        # --------------------------
        # Guardar archivo temporal
        # --------------------------

        suffix = os.path.splitext(file.filename)[1]

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
        ) as temp_file:

            content = await file.read()
            temp_file.write(content)

            temp_path = temp_file.name

        try:

            print("\n========== OCR ==========\n")

            ocr_result = ocr_service.extract_text(temp_path)

            print(ocr_result["text"])

            print("\n========== LLM ==========\n")

            document = llm_service.extract_document(
                ocr_result["text"]
            )

            print(document)

            invoice = Invoice(

                supplier_name=document["supplier"].get("name"),
                supplier_nit=document["supplier"].get("tax_id"),

                invoice_number=document["invoice"].get("number"),
                issue_date=document["invoice"].get("date"),

                subtotal=self._to_float(
                    document["amounts"].get("subtotal")
                ),

                tax=self._to_float(
                    document["amounts"].get("tax_total")
                ),

                total=self._to_float(
                    document["amounts"].get("total")
                ),

                original_filename=file.filename,

                # Estos se llenarán cuando n8n procese Drive
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
                "filename": file.filename,
                "invoice": document,
            }

        finally:

            if os.path.exists(temp_path):
                os.remove(temp_path)