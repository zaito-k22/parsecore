import asyncio
import json

from app.integrations.siigo.service import SiigoService


async def main():

    universal_json = {
        "supplier": {
            "name": "ByteDance",
            "tax_id": "900123456",
            "address": None,
            "phone": None,
            "email": None,
        },
        "customer": {
            "name": None,
            "tax_id": None,
            "address": None,
        },
        "invoice": {
            "number": "FV-12345",
            "date": "2026-07-31",
            "currency": "COP",
            "payment_method": None,
            "purchase_order": None,
        },
        "amounts": {
            "subtotal": 300000,
            "discount": None,
            "tax_total": 57000,
            "retentions": None,
            "total": 357000,
        },
        "taxes": [
            {
                "name": "IVA",
                "rate": 19,
                "amount": 57000,
            }
        ],
        "items": [
            {
                "description": "Servicio de prueba",
                "quantity": 2,
                "unit_price": 150000,
                "subtotal": 300000,
                "tax": 57000,
            }
        ],
        "additional_fields": {},
    }

    service = SiigoService()

    purchase_invoice = service.build_purchase_invoice(
        universal_json,
    )

    print(
        json.dumps(
            purchase_invoice.model_dump(),
            indent=4,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())