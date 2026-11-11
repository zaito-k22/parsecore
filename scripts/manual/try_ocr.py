import os
import sys

from app.services.ocr.service import ocr_service


def main() -> int:
    if len(sys.argv) < 2:
        print(
            "Uso: python -m scripts.manual.try_ocr <ruta-al-pdf>\n"
            "Ejemplo: python -m scripts.manual.try_ocr tests/samples/CertificadoPos.pdf",
            file=sys.stderr,
        )
        return 1

    pdf_path = sys.argv[1]

    if not os.path.exists(pdf_path):
        print(f"Archivo no encontrado: {pdf_path}", file=sys.stderr)
        return 1

    resultado = ocr_service.extract_text(pdf_path)
    print(resultado)
    return 0


if __name__ == "__main__":
    sys.exit(main())