from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from sqlalchemy.orm import Session

from app.core.invoice_status import normalize_status
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


@router.get("s", response_model=InvoiceListResponse)
def list_invoices(
    response: Response,
    status: Annotated[str | None, Query()] = None,
    from_date: Annotated[date | None, Query(alias="from")] = None,
    to_date: Annotated[date | None, Query(alias="to")] = None,
    supplier: Annotated[str | None, Query()] = None,
    tax_id: Annotated[str | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 100,
    db: Session = Depends(get_db),
):

    if from_date is not None and to_date is not None and from_date > to_date:
        raise HTTPException(
            status_code=422,
            detail="'from' no puede ser posterior a 'to'.",
        )

    normalized_status = None

    if status is not None:
        try:
            normalized_status = normalize_status(status)
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail=str(exc),
            ) from None

    service = InvoiceService(db)

    invoices, total = service.list(
        status=normalized_status,
        from_date=from_date,
        to_date=to_date,
        supplier=supplier,
        tax_id=tax_id,
        page=page,
        page_size=page_size,
    )

    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Page"] = str(page)
    response.headers["X-Page-Size"] = str(page_size)

    return {
        "invoices": invoices,
    }


@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
):

    service = InvoiceService(db)

    return service.get(invoice_id)


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
