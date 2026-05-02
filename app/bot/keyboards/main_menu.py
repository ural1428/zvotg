from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

main_menu_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
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
