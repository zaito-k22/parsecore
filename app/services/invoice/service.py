import json
import os
import re
import tempfile


from fastapi import UploadFile
from sqlalchemy.orm import Session


from app.exceptions.invoice import InvoiceNotFound
from app.models.invoice import Invoice
from app.repositories.invoice_repository import InvoiceRepository
from app.services.llm.service import llm_service
from app.services.ocr.service import ocr_service
from app.integrations.siigo.service import SiigoService


class InvoiceService:

    def __init__(self, db: Session):
        self.repository = InvoiceRepository(db)

    @staticmethod
    def _to_float(value):

        if value in (None, ""):
            return None

        if isinstance(value, (int, float)):
            return float(value)

        value = str(value).strip()

        # Eliminar símbolos de moneda y cualquier otro carácter no numérico
        value = re.sub(r"[^\d,.-]", "", value)

        if "," in value:
            value = value.replace(".", "")
            value = value.replace(",", ".")

        try:
            return float(value)

        except ValueError:
            return None

    async def process(self, file: UploadFile):

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

            print("\n========== SIIGO ==========\n")

            siigo_service = SiigoService()

            purchase_invoice = siigo_service.build_purchase_invoice(
                document,
            )

            print(
                json.dumps(
                    purchase_invoice.model_dump(),
                    indent=4,
                    ensure_ascii=False,
                )
            )

            # TEMPORAL: verificar las claves que devuelve el LLM
            print("\n========== AMOUNTS ==========\n")
            print(document.get("amounts"))

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