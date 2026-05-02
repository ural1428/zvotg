from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def select_subscription_keyboard(subscriptions) -> InlineKeyboardMarkup:
    keyboard = []

    for index, subscription in enumerate(subscriptions, start=1):
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"🔐 IKEv2 VPN #{index}",
                    callback_data=f"renew_sub:{subscription.cer_id}",
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                text="⬅ Назад",
                callback_data="profile:subscriptions",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)
