import os

os.environ["FLAGS_use_mkldnn"] = "0"
os.environ["PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT"] = "0"

import io
from pathlib import Path

import fitz
import numpy as np
from PIL import Image
from paddleocr import PaddleOCR

class OCRService:
    def __init__(self):
        print("Inicializando PaddleOCR...")

        self.ocr = PaddleOCR(
            lang="es",
            device="cpu",
        )

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

        raise ValueError(f"Formato no soportado: {extension}")

    def _extract_from_image(self, image_path: str):
        """
        Ejecuta OCR sobre una imagen.
        """
        return self._predict(image_path)

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

                print(f"[OCR] Procesando página {page_number}/{total_pages}")

                # Renderizar la página a 300 DPI
                pix = page.get_pixmap(dpi=300)

                # Convertir a bytes PNG
                image_bytes = pix.tobytes("png")

                # Abrir con Pillow
                image = Image.open(io.BytesIO(image_bytes))

                # Convertir a NumPy
                image_array = np.array(image)

                # Ejecutar OCR
                formatted = self._predict(image_array)

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

    def _predict(self, image):
        """
        Ejecuta PaddleOCR y normaliza su salida.
        """

        result = self.ocr.predict(image)

        return self._format_result(result)

    def _format_result(self, result):
        """
        Convierte la salida de PaddleOCR en el formato estándar del proyecto.
        """

        if not result:
            return {
                "text": "",
                "lines": [],
                "line_confidences": [],
                "pages": 1,
            }

        page = result[0]

        lines = page.get("rec_texts", [])
        confidences = page.get("rec_scores", [])

        text = "\n".join(lines)

        return {
            "text": text,
            "lines": lines,
            "line_confidences": confidences,
            "pages": 1,
        }


ocr_service = OCRService()
