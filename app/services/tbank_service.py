import hashlib
from typing import Any

import aiohttp

from app.config import config
from app.database.models import Order
from app.services.tariffs import TARIFFS


def _stringify(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"

    return str(value)


def generate_tbank_token(data: dict[str, Any]) -> str:
    token_data = {}

    for key, value in data.items():
        if key == "Token":
            continue

        if isinstance(value, (dict, list)):
            continue

        if value is None:
            continue

        token_data[key] = value

    token_data["Password"] = config.tbank_password

    values = [
        _stringify(token_data[key])
        for key in sorted(token_data.keys())
    ]

    raw = "".join(values)

    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def init_tbank_payment(order: Order) -> dict:
    tariff = TARIFFS[order.tariff_code]

    amount_kopecks = int(order.amount) * 100
    public_order_id = order.public_order_id or str(order.id)

    payload = {
        "TerminalKey": config.tbank_terminal_key,
        "Amount": amount_kopecks,
        "OrderId": f"{config.payment_project_code}-{order.id}-{public_order_id}",
        "Description": f"{config.payment_service_description}: {tariff['title']}",
        "CustomerKey": get_order_customer_key(order),
        "NotificationURL": f"{config.public_webhook_base_url}/payments/tbank/webhook",
        "SuccessURL": f"{config.public_webhook_base_url}/payments/success",
        "FailURL": f"{config.public_webhook_base_url}/payments/fail",
        "DATA": {
            "telegram_id": str(order.telegram_id or ""),
            "owner_platform": order.owner_platform or "tg",
            "owner_external_id": str(order.owner_external_id or order.telegram_id or ""),
            "order_id": str(order.id),
            "public_order_id": str(public_order_id),
            "action": order.action,
            "cer_id": order.cer_id or "",
            "service": config.payment_service_code,
            "project": config.payment_project_code,
        },
        "Receipt": build_receipt(order),
    }

    payload["Token"] = generate_tbank_token(payload)

    async with aiohttp.ClientSession() as http:
        async with http.post(
            config.tbank_init_url,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            data = await response.json(content_type=None)

    if not data.get("Success"):
        raise RuntimeError(f"T-Bank Init failed: {data}")

    return data

def build_receipt(order: Order) -> dict:
    if not order.customer_email:
        raise ValueError("customer_email is required for receipt")

    amount_kopecks = int(order.amount) * 100
    tariff = TARIFFS[order.tariff_code]

    item_name = f"{config.payment_service_description}: {tariff['title']}"

    return {
        "Email": order.customer_email,
        "Taxation": config.receipt_taxation,
        "Items": [
            {
                "Name": item_name,
                "Price": amount_kopecks,
                "Quantity": 1,
                "Amount": amount_kopecks,
                "PaymentMethod": config.receipt_payment_method,
                "PaymentObject": config.receipt_payment_object,
                "Tax": config.receipt_tax,
            }
        ],
    }

def get_order_customer_key(order: Order) -> str:
    if order.owner_platform and order.owner_external_id:
        return f"{order.owner_platform}:{order.owner_external_id}"

    return f"tg:{order.telegram_id}"

def verify_tbank_notification(data: dict[str, Any]) -> bool:
    received_token = data.get("Token")

    if not received_token:
        return False

    expected_token = generate_tbank_token(data)

    return received_token == expected_token
