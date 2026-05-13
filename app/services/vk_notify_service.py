import json
import os
import random
from typing import Any

import aiohttp
from dotenv import load_dotenv


load_dotenv()

VK_BOT_TOKEN = os.getenv("VK_BOT_TOKEN")
VK_API_VERSION = os.getenv("VK_API_VERSION", "5.199")
VK_API_URL = "https://api.vk.com/method"


async def vk_api_call(
    method: str,
    params: dict[str, Any] | None = None,
):
    if not VK_BOT_TOKEN:
        raise RuntimeError("VK_BOT_TOKEN не найден в .env")

    payload = {
        "access_token": VK_BOT_TOKEN,
        "v": VK_API_VERSION,
    }

    if params:
        payload.update(params)

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{VK_API_URL}/{method}",
            data=payload,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            data = await response.json(content_type=None)

    if "error" in data:
        raise RuntimeError(f"VK API error: {data['error']}")

    return data["response"]


async def send_vk_message(
    peer_id: int,
    message: str,
    keyboard: dict[str, Any] | None = None,
):
    params = {
        "peer_id": peer_id,
        "message": message,
        "random_id": random.randint(1, 2_147_483_647),
    }

    if keyboard:
        params["keyboard"] = json.dumps(
            keyboard,
            ensure_ascii=False,
        )

    return await vk_api_call("messages.send", params)
