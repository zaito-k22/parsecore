from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.invoice import (
    InvoiceListResponse,
    InvoiceResponse,
    InvoiceUpdate,
)
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

    service = InvoiceService(db)

    return await service.process(file)


@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
):

    service = InvoiceService(db)

    return service.get(invoice_id)


@router.get("s", response_model=InvoiceListResponse)
def list_invoices(
    db: Session = Depends(get_db),
):

    service = InvoiceService(db)

    return {
        "invoices": service.list(),
    }


@router.patch("/{invoice_id}", response_model=InvoiceResponse)
def update_invoice(
    invoice_id: int,
    body: InvoiceUpdate,
    db: Session = Depends(get_db),
):

    service = InvoiceService(db)

    return service.update(
        invoice_id,
        body.status,
        body.drive_file_id,
        body.drive_folder,
    )


@router.delete("/{invoice_id}")
def delete_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
):

    service = InvoiceService(db)

    service.delete(invoice_id)

    return {
        "success": True,
    }