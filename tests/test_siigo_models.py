import asyncio

from app.integrations.siigo.service import SiigoService


async def main():
    service = SiigoService()

    supplier = await service.find_supplier_by_identification(
        "81-2345210"
    )

    print(type(supplier))
    print(supplier.identification)
    print(supplier.name)


asyncio.run(main())