import base64
import json
import uuid
from pathlib import Path

from app.config import config


def create_strongswan_profile(
    cer_id: str,
    p12_path: str,
) -> str:
    p12_file = Path(p12_path)

    if not p12_file.exists():
        raise FileNotFoundError(f"Certificate not found: {p12_path}")

    output_dir = Path("./storage/strongswan")
    output_dir.mkdir(parents=True, exist_ok=True)

    profile_path = output_dir / f"{cer_id}.sswan"

    p12_base64 = base64.b64encode(p12_file.read_bytes()).decode("utf-8")

    profile = {
        "uuid": str(uuid.uuid4()),
        "name": f"{config.vpn_profile_name} {cer_id}",
        "type": "ikev2-cert",
        "remote": {
            "addr": config.vpn_server_host,
        },
        "local": {
            "p12": p12_base64,
        },

        "ike-proposal": "aes256-sha256-modp2048",

        "esp-proposal": "aes256-sha256",

        "port": 4500,

        "mtu": 1400
    }

    profile_path.write_text(
        json.dumps(profile, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return str(profile_path)
