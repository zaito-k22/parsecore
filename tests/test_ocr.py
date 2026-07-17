from app.services.ocr.service import ocr_service

resultado = ocr_service.extract_text("tests/samples/CertificadoPos.pdf")

print(resultado)
