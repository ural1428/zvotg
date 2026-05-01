from app.integrations.mikrotik.client import (
    MikroTikSSHClient,
)

from app.integrations.mikrotik.scp import (
    MikroTikSCPClient,
)

from app.integrations.mikrotik.commands import (
    build_new_cert_command,
    build_disable_cert_command,
    build_renew_cert_command,
    build_remove_file_command,
)


class MikroTikCertService:

    def __init__(
        self,
        client: MikroTikSSHClient,
        scp_client: MikroTikSCPClient,
    ):

        self.client = client
        self.scp = scp_client

    async def create_cert(
        self,
        cert_id: int,
    ):

        command = build_new_cert_command(
            cert_id,
        )

        await self.client.execute(
            command,
        )

        file_name = f"{cert_id}.p12"

        local_path = (
            f"./storage/certs/{file_name}"
        )

        await self.scp.download_file(
            remote_path=file_name,
            local_path=local_path,
        )

        remove_command = (
            build_remove_file_command(
                cert_id,
            )
        )

        await self.client.execute(
            remove_command,
        )

        return local_path

    async def disable_cert(
        self,
        cert_id: list[int],
    ):

        command = build_disable_cert_command(
            cert_id,
        )

        return await self.client.execute(
            command,
        )

    async def renew_cert(
        self,
        cert_id: int,
    ):

        command = build_renew_cert_command(
            cert_id,
        )

        return await self.client.execute(
            command,
        )

    async def download_cert(
        self,
        remote_path: str,
        local_path: str,
    ):

        await self.scp.download_file(
            remote_path=remote_path,
            local_path=local_path,
        )
