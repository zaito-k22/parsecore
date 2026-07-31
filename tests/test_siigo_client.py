import asyncio

from app.integrations.siigo.client import SiigoClient


async def main():
    client = SiigoClient()

    print("Primera petición")
    await client.get("/customers")

    print("Segunda petición")
    await client.get("/customers")

    print("Tercera petición")
    await client.get("/customers")

    print("Todo OK")


asyncio.run(main())