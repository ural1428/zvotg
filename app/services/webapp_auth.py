import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from app.config import config


class WebAppAuthError(Exception):
    pass


def validate_telegram_init_data(
    init_data: str,
    max_age_seconds: int = 86400,
) -> dict:
    if not init_data:
        raise WebAppAuthError("initData is empty")

    parsed = dict(parse_qsl(init_data, keep_blank_values=True))

    received_hash = parsed.pop("hash", None)

    if not received_hash:
        raise WebAppAuthError("hash is missing")

    data_check_string = "\n".join(
        f"{key}={value}"
        for key, value in sorted(parsed.items())
    )

    secret_key = hmac.new(
        b"WebAppData",
        config.bot_token.encode("utf-8"),
        hashlib.sha256,
    ).digest()

    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        raise WebAppAuthError("invalid hash")

    auth_date = int(parsed.get("auth_date", "0") or 0)

    if auth_date and time.time() - auth_date > max_age_seconds:
        raise WebAppAuthError("initData is expired")

    user_raw = parsed.get("user")

    if not user_raw:
        raise WebAppAuthError("user is missing")

    user = json.loads(user_raw)

    if "id" not in user:
        raise WebAppAuthError("user id is missing")

    return {
        "telegram_id": int(user["id"]),
        "user": user,
        "raw": parsed,
    }
