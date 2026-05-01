from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
)


main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(
                text="Создать VPN",
            ),
        ],
        [
            KeyboardButton(
                text="Мои сертификаты",
            ),
        ],
    ],
    resize_keyboard=True,
)
