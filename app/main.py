import logging

from fastapi import FastAPI

from app.core.config import settings

# El logging se configura antes de importar los módulos que cargan
# OCR y LLM al importarse, para no perder sus mensajes de arranque.
logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

from app.api.invoice import router as invoice_router  # noqa: E402
from app.exceptions.handlers import register_exception_handlers  # noqa: E402

app = FastAPI(
    title="Facturas AI",
    description="API para extracción inteligente de información de facturas.",
    version="0.1.0",
)

register_exception_handlers(app)


@app.get("/")
async def root():
    return {
        "status": "ok",
        "version": "0.1.0",
        "message": "Facturas AI funcionando correctamente",
    }


app.include_router(invoice_router)