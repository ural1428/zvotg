from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.services.tariffs import TARIFFS


def tariffs_keyboard(
    action: str,
    back_callback: str = "menu:main",
    cer_id: str | None = None,
) -> InlineKeyboardMarkup:
    keyboard = []

    for code, tariff in TARIFFS.items():
        if cer_id:
            callback_data = f"tariff:{action}:{cer_id}:{code}"
        else:
            callback_data = f"tariff:{action}:{code}"

        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"{tariff['title']} — {tariff['amount']} ₽",
                    callback_data=callback_data,
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
