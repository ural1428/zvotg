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
    bot_username: str
    db: DatabaseConfig
    mikrotik: MikroTikConfig
    vpn_server_host: str
    vpn_profile_name: str
    cert_password: str
    easter_egg_code: str | None
    tbank_terminal_key: str
    tbank_password: str
    tbank_init_url: str
    public_webhook_base_url: str
    payment_project_code: str
    payment_service_description: str
    payment_service_code: str
config = Config(
    bot_token=os.getenv("BOT_TOKEN"),
    bot_username=os.getenv("BOT_USERNAME"),
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
    easter_egg_code=os.getenv("EASTER_EGG_CODE"),
    tbank_terminal_key=os.getenv("TBANK_TERMINAL_KEY"),
    tbank_password=os.getenv("TBANK_PASSWORD"),
    tbank_init_url=os.getenv("TBANK_INIT_URL", "https://securepay.tinkoff.ru/v2/Init"),
    public_webhook_base_url=os.getenv("PUBLIC_WEBHOOK_BASE_URL"),

    payment_project_code=os.getenv("PAYMENT_PROJECT_CODE", "uplink-spb"),
    payment_service_description=os.getenv(
        "PAYMENT_SERVICE_DESCRIPTION",
        "Подписка на обслуживание",
    ),
    payment_service_code=os.getenv(
        "PAYMENT_SERVICE_CODE",
        "maintenance_subscription",
    ),
)
