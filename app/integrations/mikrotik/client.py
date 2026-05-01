import asyncio

import asyncssh

from loguru import logger

from app.integrations.mikrotik.base import (
    MikroTikBaseClient,
)


class MikroTikSSHClient(
    MikroTikBaseClient,
):

    async def execute(
        self,
        command: str,
    ) -> str:

        logger.info(
            f"Connecting to MikroTik {self.host}",
        )

        try:

            conn = await asyncio.wait_for(
                asyncssh.connect(
                    host=self.host,
                    port=self.port,
                    username=self.username,
                    client_keys=[self.ssh_key_path],
                    known_hosts=None,
                ),
                timeout=self.timeout,
            )

            async with conn:

                print(repr(command))

                result = await asyncio.wait_for(
                    conn.run(
                        command,
                        check=False,
                    ),
                    timeout=180,
                )

                logger.info(
                    f"Exit status: {result.exit_status}",
                )

                if result.stdout:
                    logger.info(
                        f"STDOUT:\n{result.stdout}",
                    )

                if result.stderr:
                    logger.error(
                        f"STDERR:\n{result.stderr}",
                    )

                return result.stdout.strip()

        except asyncio.TimeoutError:

            logger.error(
                "MikroTik command timeout",
            )

            raise

        except asyncssh.Error as e:

            logger.exception(
                f"SSH error: {e}",
            )

            raise

        except Exception as e:

            logger.exception(
                f"Unexpected error: {e}",
            )

            raise
