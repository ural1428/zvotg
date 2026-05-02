from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


profile_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📦 Мои подписки",
                callback_data="profile:subscriptions",
            )
        ],
        [
            InlineKeyboardButton(
                text="⬅ Назад",
                callback_data="menu:main",
            )
        ],
    ]
)


subscriptions_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🔄 Продлить подписку",
                callback_data="subscription:renew",
            )
        ],
        [
            InlineKeyboardButton(
                text="📄 Скачать сертификат",
                callback_data="subscription:download_cert",
            )
        ],
        [
            InlineKeyboardButton(
                text="⬅ Назад",
                callback_data="menu:profile",
            )
        ],
    ]
)
