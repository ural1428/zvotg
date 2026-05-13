import os

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo


WEBAPP_URL = os.getenv("WEBAPP_URL", "https://mymayak.ru/webapp/")


def main_menu_keyboard(user_id: int | None = None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🚀 Открыть приложение",
                    web_app=WebAppInfo(url=WEBAPP_URL),
                )
            ],
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
    )