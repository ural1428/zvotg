from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.services.tariffs import TARIFFS


def tariffs_keyboard(back_callback: str = "menu:main") -> InlineKeyboardMarkup:
    keyboard = []

    for code, tariff in TARIFFS.items():
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"{tariff['title']} — {tariff['amount']} ₽",
                    callback_data=f"tariff:select:{code}",
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                text="⬅ Назад",
                callback_data=back_callback,
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)
