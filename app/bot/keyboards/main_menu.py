import os

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo


WEBAPP_URL = os.getenv("WEBAPP_URL", "https://mymayak.ru/webapp/")


def get_webapp_tester_ids() -> set[int]:
    raw_ids = os.getenv("WEBAPP_TESTER_IDS", "")

    tester_ids = set()

    for raw_id in raw_ids.split(","):
        raw_id = raw_id.strip()

        if raw_id.isdigit():
            tester_ids.add(int(raw_id))

    return tester_ids


def main_menu_keyboard(user_id: int | None = None) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(
                text="👤 Профиль",
                callback_data="menu:profile",
            )
        ],
        [
            InlineKeyboardButton(
                text="💳 Купить подписку",
                callback_data="menu:buy",
            )
        ],
        [
            InlineKeyboardButton(
                text="📋 Тарифы",
                callback_data="menu:tariffs",
            )
        ],
        [
            InlineKeyboardButton(
                text="🛠 Поддержка",
                callback_data="menu:support",
            )
        ],
    ]

    if user_id in get_webapp_tester_ids():
        keyboard.insert(
            0,
            [
                InlineKeyboardButton(
                    text="🚀 Открыть приложение",
                    web_app=WebAppInfo(url=WEBAPP_URL),
                )
            ],
        )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)