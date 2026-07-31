from app.integrations.siigo.invoice_schema.invoice import Invoice
from app.integrations.siigo.invoice_schema.item import InvoiceItem
from app.integrations.siigo.invoice_schema.supplier import Supplier
from app.integrations.siigo.invoice_schema.totals import InvoiceTotals


class SchemaMapper:

    def map(
        self,
        raw_invoice: dict,
    ) -> Invoice:

        supplier = raw_invoice.get("supplier", {})
        invoice = raw_invoice.get("invoice", {})
        amounts = raw_invoice.get("amounts", {})

        items = []

        for item in raw_invoice.get("items", []):
            items.append(
                InvoiceItem(
                    description=item.get("description"),
                    quantity=float(item.get("quantity", 0)),
                    unit_price=float(item.get("unit_price", 0)),
                    tax_percentage=float(
                        item.get("tax_percentage", 0)
                    ),
                    discount=item.get("discount"),
                )
            )

        return Invoice(
            supplier=Supplier(
                identification=str(
                    supplier.get("tax_id") or ""
                ),
                name=supplier.get("name") or "",
            ),
            date=invoice.get("date"),
            number=invoice.get("number"),
            observations=invoice.get("observations"),
            items=items,
            totals=InvoiceTotals(
                subtotal=float(
                    amounts.get("subtotal", 0)
                ),
                tax=float(
                    amounts.get("tax_total", 0)
                ),
                total=float(
                    amounts.get("total", 0)
                ),
            ),
        )