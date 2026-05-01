import asyncio

from app.config import config

from app.integrations.mikrotik.manager import (
    MikroTikManager,
)


async def main():

    mikrotik = MikroTikManager(
        config=config.mikrotik,
    )

    file_name = await mikrotik.certs.create_cert(
        cert_id=112345,
    )

    print(file_name)


if __name__ == "__main__":

    asyncio.run(main())
