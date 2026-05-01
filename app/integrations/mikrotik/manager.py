from app.config import MikroTikConfig

from app.integrations.mikrotik.client import (
    MikroTikSSHClient
)

from app.integrations.mikrotik.scp import (
    MikroTikSCPClient
)

from app.integrations.mikrotik.certs import (
    MikroTikCertService
)


class MikroTikManager:

    def __init__(
        self,
        config: MikroTikConfig,
    ):

        self.ssh = MikroTikSSHClient(
            config
        )

        self.scp = MikroTikSCPClient(
            config
        )

        self.certs = MikroTikCertService(
            client=self.ssh,
            scp_client=self.scp,
        )
