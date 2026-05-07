from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


reply_menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Главное меню"),
        ],
        [
            KeyboardButton(text="Профиль"),
            KeyboardButton(text="Тарифы"),
        ],
        [
            KeyboardButton(text="Поддержка"),
        ],
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите действие",
)