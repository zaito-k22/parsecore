from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.invoice.service import InvoiceService

router = APIRouter(
    prefix="/invoice",
    tags=["Invoice"],
)


@router.post("")
async def upload_invoice(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Procesa una factura,
    la guarda en PostgreSQL
    y devuelve el JSON generado.
    """

    try:

        service = InvoiceService(db)

        return await service.process(file)

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )