from app.config import MikroTikConfig


class MikroTikBaseClient:

    def __init__(
        self,
        config: MikroTikConfig,
        timeout: int = 10,
    ):

        self.host = config.host
        self.username = config.user
        self.port = config.port
        self.ssh_key_path = config.ssh_key

        self.timeout = timeout
