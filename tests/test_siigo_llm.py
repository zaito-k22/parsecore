from app.integrations.siigo.llm_service import SiigoLLMService


def main():

    text = """
FACTURA

Proveedor:
ByteDance

NIT:
900123456

Factura:
FV-12345

Fecha:
2026-07-31

Servicio de prueba

Cantidad:
2

Valor:
150000

IVA:
19%

TOTAL:
357000
"""

    llm = SiigoLLMService()

    response = llm.generate(text)

    print(response)


if __name__ == "__main__":
    main()