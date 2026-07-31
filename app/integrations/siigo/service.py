import json

from app.integrations.siigo.builders.purchase_invoice_builder import (
    PurchaseInvoiceBuilder,
)
from app.integrations.siigo.client import SiigoClient
from app.integrations.siigo.llm_service import SiigoLLMService
from app.integrations.siigo.models.customer import SiigoCustomer
from app.integrations.siigo.models.purchase_invoice.purchase_invoice import (
    PurchaseInvoiceRequest,
)
from app.integrations.siigo.models.supplier import SiigoSupplier
from app.integrations.siigo.schema_mapper import SchemaMapper


class SiigoService:

    def __init__(self):
        self.client = SiigoClient()

        self.llm = SiigoLLMService()

        self.mapper = SchemaMapper()

        self.builder = PurchaseInvoiceBuilder()

    async def get_customers(self) -> list[SiigoCustomer]:

        response = await self.client.get("/customers")

        results = response.get("results", [])

        return [
            SiigoCustomer.model_validate(customer)
            for customer in results
        ]

    async def get_suppliers(self) -> list[SiigoSupplier]:

        response = await self.client.get(
            "/customers",
            params={
                "type": "Supplier",
            },
        )

        results = response.get("results", [])

        return [
            SiigoSupplier.model_validate(supplier)
            for supplier in results
        ]

    async def find_customer_by_identification(
        self,
        identification: str,
    ) -> SiigoCustomer | None:

        response = await self.client.get(
            "/customers",
            params={
                "identification": identification,
            },
        )

        results = response.get("results", [])

        if not results:
            return None

        return SiigoCustomer.model_validate(results[0])

    async def find_supplier_by_identification(
        self,
        identification: str,
    ) -> SiigoSupplier | None:

        response = await self.client.get(
            "/customers",
            params={
                "identification": identification,
                "type": "Supplier",
            },
        )

        results = response.get("results", [])

        if not results:
            return None

        return SiigoSupplier.model_validate(results[0])

    def build_purchase_invoice(
        self,
        universal_json: dict,
    ) -> PurchaseInvoiceRequest:

        siigo_json = self.llm.generate(
            json.dumps(
                universal_json,
                ensure_ascii=False,
            )
        )

        invoice = self.mapper.map(
            json.loads(siigo_json),
        )

        return self.builder.build(
            invoice,
        )