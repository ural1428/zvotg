from aiogram import (
    Router,
)

from aiogram.types import (
    Message,
)

from app.bot.keyboards.reply import (
    main_keyboard,
)

router = Router()


@router.message()
async def start_handler(
    message: Message,
):

    await message.answer(
        "VPN Bot запущен",
        reply_markup=main_keyboard,
    )
