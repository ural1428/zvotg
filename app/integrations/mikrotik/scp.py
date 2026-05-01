import asyncio
import asyncssh

from loguru import logger

from app.integrations.mikrotik.base import (
    MikroTikBaseClient
)


class MikroTikSCPClient(
    MikroTikBaseClient
):

    async def download_file(
        self,
        remote_path: str,
        local_path: str,
    ):

        logger.info(
            f"Downloading {remote_path}"
        )

        conn = await asyncio.wait_for(
            asyncssh.connect(
                host=self.host,
                username=self.username,
                port=self.port,
                client_keys=[self.ssh_key_path],
                known_hosts=None,
            ),
            timeout=self.timeout,
        )

        async with conn:

            await asyncio.wait_for(
                asyncssh.scp(
                    (conn, remote_path),
                    local_path,
                ),
                timeout=self.timeout,
            )

        logger.success(
            f"Downloaded {local_path}"
        )
