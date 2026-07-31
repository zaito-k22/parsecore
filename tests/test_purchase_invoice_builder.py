import json

from app.integrations.siigo.builders.purchase_invoice_builder import (
    PurchaseInvoiceBuilder,
)
from app.integrations.siigo.schema_mapper import SchemaMapper


def main():

    raw_invoice = {
        "whatever": "ocr json",
    }

    mapper = SchemaMapper()

    invoice = mapper.map(raw_invoice)

    builder = PurchaseInvoiceBuilder()

    purchase_invoice = builder.build(invoice)

    print(
        json.dumps(
            purchase_invoice.model_dump(),
            indent=4,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()