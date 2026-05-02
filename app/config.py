from dataclasses import dataclass
from dotenv import load_dotenv
import os

load_dotenv()


@dataclass
class DatabaseConfig:
    host: str
    port: int
    name: str
    user: str
    password: str

@dataclass
class MikroTikConfig:
    host: str
    user: str
    port: int
    ssh_key: str

@dataclass
class Config:
    bot_token: str
    db: DatabaseConfig
    mikrotik: MikroTikConfig
    vpn_server_host: str
    vpn_profile_name: str
    cert_password: str
config = Config(
    bot_token=os.getenv("BOT_TOKEN"),
    db=DatabaseConfig(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT")),
        name=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
    ),
    mikrotik=MikroTikConfig(
        host=os.getenv("MIKROTIK_HOST"),
        user=os.getenv("MIKROTIK_USER"),
        port=int(os.getenv("MIKROTIK_PORT")),
        ssh_key=os.getenv("MIKROTIK_SSH_KEY"),
    ),
    vpn_server_host=os.getenv("VPN_SERVER_HOST"),
    vpn_profile_name=os.getenv("VPN_PROFILE_NAME", "ZVO VPN"),
    cert_password=os.getenv("CERT_PASSWORD", "123456789"),
)
