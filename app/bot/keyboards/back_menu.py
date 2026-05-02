from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


back_to_main_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="⬅ Назад",
                callback_data="menu:main"
            )
        ]
    ]
)
