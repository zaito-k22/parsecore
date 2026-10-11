from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.exceptions.invoice import (
    InvoiceNotFound,
    LLMExtractionError,
    UnsupportedFileFormat,
)


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

    @app.exception_handler(UnsupportedFileFormat)
    async def unsupported_format_handler(
        request: Request,
        exc: UnsupportedFileFormat,
    ):

        return JSONResponse(
            status_code=415,
            content={
                "detail": f"Unsupported file format: {exc.extension or '(none)'}",
            },
        )

    @app.exception_handler(LLMExtractionError)
    async def llm_extraction_handler(
        request: Request,
        exc: LLMExtractionError,
    ):

        return JSONResponse(
            status_code=502,
            content={
                "detail": "The extraction model returned an invalid response",
            },
        )
