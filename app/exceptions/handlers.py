from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.exceptions.invoice import InvoiceNotFound


def register_exception_handlers(app: FastAPI):

    @app.exception_handler(InvoiceNotFound)
    async def invoice_not_found_handler(
        request: Request,
        exc: InvoiceNotFound,
    ):

        return JSONResponse(
            status_code=404,
            content={
                "detail": f"Invoice {exc.invoice_id} not found",
            },
        )