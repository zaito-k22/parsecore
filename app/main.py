from fastapi import FastAPI, UploadFile, File

from app.services.invoice.service import InvoiceService

app = FastAPI(
    title="Facturas AI",
    description="API para extracción inteligente de información de facturas.",
    version="0.1.0",
)

invoice_service = InvoiceService()


@app.get("/")
async def root():
    return {
        "status": "ok",
        "version": "0.1.0",
        "message": "Facturas AI funcionando correctamente",
    }


@app.post("/invoice")
async def upload_invoice(file: UploadFile = File(...)):
    return await invoice_service.process(file)