import asyncio

from app.integrations.siigo.auth import SiigoAuth


async def main():
    auth = SiigoAuth()

    token = await auth.authenticate()

    print(token)


asyncio.run(main())