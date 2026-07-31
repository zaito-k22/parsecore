import asyncio

from app.integrations.siigo.models.purchase_invoice.document import (
    PurchaseInvoiceDocument,
)
from app.integrations.siigo.models.purchase_invoice.item import (
    PurchaseInvoiceItem,
)
from app.integrations.siigo.models.purchase_invoice.payment import (
    PurchaseInvoicePayment,
)
from app.integrations.siigo.models.purchase_invoice.purchase_invoice import (
    PurchaseInvoiceRequest,
)
from app.integrations.siigo.models.purchase_invoice.supplier import (
    PurchaseInvoiceSupplier,
)
from app.integrations.siigo.models.purchase_invoice.tax import (
    PurchaseInvoiceTax,
)


async def main():
    invoice = PurchaseInvoiceRequest(
        document=PurchaseInvoiceDocument(
            id=1,
        ),
        supplier=PurchaseInvoiceSupplier(
            identification="900123456",
        ),
        date="2026-07-30",
        observations="Factura de prueba",
        items=[
            PurchaseInvoiceItem(
                code="ITEM-001",
                description="Servicio de prueba",
                quantity=2,
                price=150000,
                taxes=[
                    PurchaseInvoiceTax(
                        id=13156,
                    )
                ],
            )
        ],
        payments=[
            PurchaseInvoicePayment(
                id=5636,
                value=300000,
                due_date="2026-08-30",
            )
        ],
    )

    import json

    print(
        json.dumps(
            invoice.model_dump(),
            indent=2,
            ensure_ascii=False,
        )
    )


asyncio.run(main())