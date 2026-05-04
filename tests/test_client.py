import asyncio

from app.config import config

from app.integrations.mikrotik.client import (
    MikroTikSSHClient
)


async def main():

    client = MikroTikSSHClient(
        host=config.mikrotik.host,
        username=config.mikrotik.user,
        port=config.mikrotik.port,
        ssh_key_path=config.mikrotik.ssh_key,
    )

    result = await client.execute(
        "/system identity print"
    )

    print(result)


asyncio.run(main())
