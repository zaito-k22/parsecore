from pathlib import Path
import shutil

from fastapi import APIRouter, File, UploadFile, HTTPException

from app.services.ocr.service import ocr_service
from app.services.llm.service import llm_service

router = APIRouter(prefix="/invoice", tags=["Invoice"])


@router.post("/process")
async def process_invoice(file: UploadFile = File(...)):
    """
    Procesa una factura (PDF o imagen) y devuelve la información extraída.
    """

    temp_dir = Path("temp")
    temp_dir.mkdir(exist_ok=True)

    temp_file = temp_dir / file.filename

    try:

        # Guardar el archivo temporalmente
        with open(temp_file, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # OCR
        ocr_result = ocr_service.extract_text(str(temp_file))

        # LLM
        invoice = llm_service.extract_invoice(
            ocr_result["text"]
        )

        return invoice

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        if temp_file.exists():
            temp_file.unlink()