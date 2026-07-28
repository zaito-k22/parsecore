from fastapi import FastAPI

from app.api.invoice import router as invoice_router

app = FastAPI(
    title="Facturas AI",
    description="API para extracción inteligente de información de facturas.",
    version="0.1.0",
)


@app.get("/")
async def root():
    return {
        "status": "ok",
        "version": "0.1.0",
        "message": "Facturas AI funcionando correctamente",
    }


app.include_router(invoice_router)