import os
import tempfile

from fastapi import UploadFile

from app.services.ocr.service import ocr_service
from app.services.llm.service import llm_service


class InvoiceService:

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

            return {
                "success": True,
                "filename": file.filename,
                "invoice": document,
            }

        finally:

            if os.path.exists(temp_path):
                os.remove(temp_path)