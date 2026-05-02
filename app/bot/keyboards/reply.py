from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="👤 Профиль"),
        ],
        [
            KeyboardButton(text="💳 КупитПодписку"),
            KeyboardButton(text="📦 Мои подписки"),
        ],
    ],
    resize_keyboard=True,
)
