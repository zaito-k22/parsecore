import json
import logging
import os
import select
import subprocess
import sys
from pathlib import Path
from typing import Any

os.environ["FLAGS_use_mkldnn"] = "0"
os.environ["PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT"] = "0"

import io
import tempfile

import fitz
from PIL import Image

from app.exceptions.invoice import UnsupportedFileFormat

logger = logging.getLogger(__name__)


def _run_ocr_subprocess(image_path: str, timeout: int = 120) -> dict[str, Any] | None:
    """
    Ejecuta OCR en un subprocess independiente para aislar segfaults.

    Lee la salida del proceso de forma no bloqueante para evitar esperar
    al segfault que ocurre después de imprimir el resultado.
    """
    worker_script = f'''
import sys
import json
import logging
import os
logging.basicConfig(level=logging.WARNING)

os.environ["FLAGS_use_mkldnn"] = "0"
os.environ["PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT"] = "0"

try:
    from paddleocr import PaddleOCR
    ocr = PaddleOCR(lang="es", device="cpu")
    result = ocr.predict({json.dumps(image_path)})
    if not result:
        print(json.dumps({{"text": "", "lines": [], "line_confidences": [], "pages": 1}}))
        sys.stdout.flush()
        sys.exit(0)
    page = result[0]
    lines = page.get("rec_texts", [])
    confidences = page.get("rec_scores", [])
    text = "\\n".join(lines)
    print(json.dumps({{"text": text, "lines": lines, "line_confidences": confidences, "pages": 1}}))
    sys.stdout.flush()
except Exception as e:
    print(json.dumps({{"error": str(e)}}))
    sys.stdout.flush()
'''

    try:
        proc = subprocess.Popen(
            [sys.executable, "-c", worker_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env={
                **os.environ,
                "PYTHONUNBUFFERED": "1",
            },
        )

        stdout_fd = proc.stdout.fileno()

        try:
            ready, _, _ = select.select([stdout_fd], [], [], timeout)
            if not ready:
                logger.warning("OCR subprocess timeout después de %ss", timeout)
                proc.kill()
                proc.wait()
                return None

            output = proc.stdout.readline()
        except Exception as e:
            logger.warning("Error leyendo stdout del subprocess: %s", e)
            proc.kill()
            proc.wait()
            return None

        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

        if not output:
            logger.warning("OCR subprocess devolvió salida vacía")
            return None

        try:
            data = json.loads(output.strip())
            if "error" in data:
                logger.warning("OCR subprocess error: %s", data["error"])
                return None
            return data
        except json.JSONDecodeError:
            result_str = output.strip()[:200]
            logger.warning("OCR subprocess JSON inválido: %s", result_str)
            return None

    except Exception as e:
        logger.warning("Error ejecutando OCR subprocess: %s", e)
        return None


class OCRService:
    engine = "paddleocr"

    def __init__(self):
        logger.info("Inicializando OCR Service (subprocess mode)...")

    def extract_text(self, file_path: str):
        """
        Punto de entrada del servicio.

        Recibe cualquier documento soportado y decide cómo procesarlo.
        """

        extension = Path(file_path).suffix.lower()

        if extension in [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"]:
            return self._extract_from_image(file_path)

        if extension == ".pdf":
            return self._extract_from_pdf(file_path)

        raise UnsupportedFileFormat(extension)

    def _extract_from_image(self, image_path: str):
        """
        Ejecuta OCR sobre una imagen usando subprocess para aislar segfaults.
        """
        result = _run_ocr_subprocess(image_path)

        if result is not None:
            return result

        logger.warning("OCR subprocess falló, usando fallback para %s", image_path)
        return self._fallback_image(image_path)

    def _fallback_image(self, image_path: str):
        """
        Fallback OCR usando PIL e información de archivo cuando PaddleOCR falla.
        """
        try:
            if Path(image_path).suffix.lower() == ".webp":
                Image.open(image_path)
                text = f"[Imagen OCR no disponible - archivo: {Path(image_path).name}]"
                return {
                    "text": text,
                    "lines": [text],
                    "line_confidences": [0.5],
                    "pages": 1,
                }
        except Exception as e:
            logger.warning("Fallback OCR falló: %s", e)

        return {
            "text": "",
            "lines": [],
            "line_confidences": [],
            "pages": 1,
        }

    def _extract_from_pdf(self, pdf_path: str):
        """
        Convierte cada página del PDF en una imagen y ejecuta OCR.

        Devuelve un único resultado con todas las páginas unidas.
        """

        document = fitz.open(pdf_path)

        total_pages = len(document)

        all_lines = []
        all_confidences = []

        try:
            for page_number, page in enumerate(document, start=1):

                logger.info("OCR página %s/%s", page_number, total_pages)

                pix = page.get_pixmap(dpi=300)

                image_bytes = pix.tobytes("png")

                image = Image.open(io.BytesIO(image_bytes))

                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    image.save(tmp, format="PNG")
                    tmp_path = tmp.name

                try:
                    formatted = _run_ocr_subprocess(tmp_path)
                    if formatted is None:
                        logger.warning("PaddleOCR PDF falló página %s", page_number)
                        continue
                finally:
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass

                all_lines.extend(formatted["lines"])
                all_confidences.extend(formatted["line_confidences"])

        finally:
            document.close()

        return {
            "text": "\n".join(all_lines),
            "lines": all_lines,
            "line_confidences": all_confidences,
            "pages": total_pages,
        }


ocr_service = OCRService()