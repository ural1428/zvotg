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
                text="🎁 Получить 5 дней",
                callback_data="profile:referral",
            )
        ],
        [
            InlineKeyboardButton(
                text="⚙ Управление VPN",
                callback_data="menu:support",
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


def subscriptions_keyboard(has_subscriptions: bool) -> InlineKeyboardMarkup:
    keyboard = []

    if has_subscriptions:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text="🔄 Продлить подписку",
                    callback_data="subscription:renew",
                )
            ]
        )

        keyboard.append(
            [
                InlineKeyboardButton(
                    text="📄 Скачать сертификат",
                    callback_data="subscription:download_cert",
                )
            ]
        )
    else:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text="💳 Купить подписку",
                    callback_data="menu:buy",
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                text="⬅ Назад",
                callback_data="menu:profile",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)