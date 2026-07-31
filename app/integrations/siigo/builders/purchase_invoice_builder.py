from app.integrations.siigo.invoice_schema.invoice import Invoice

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


class PurchaseInvoiceBuilder:

    def build(
        self,
        invoice: Invoice,
    ) -> PurchaseInvoiceRequest:

        items = []

        for item in invoice.items:
            items.append(
                PurchaseInvoiceItem(
                    code="",
                    description=item.description,
                    quantity=item.quantity,
                    price=item.unit_price,
                    discount=item.discount,
                    taxes=[],
                )
            )

        payments = [
            PurchaseInvoicePayment(
                id=0,
                value=invoice.totals.total,
                due_date=None,
            )
        ]

        return PurchaseInvoiceRequest(
            document=PurchaseInvoiceDocument(
                id=0,
            ),
            supplier=PurchaseInvoiceSupplier(
                identification=invoice.supplier.identification,
                branch_office=0,
            ),
            date=invoice.date,
            observations=invoice.observations,
            items=items,
            payments=payments,
        )