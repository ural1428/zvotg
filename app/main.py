import asyncio

from aiogram import (
    Bot,
)

from app.config import (
    config,
)

from app.bot.dispatcher import (
    setup_dispatcher,
)


async def main():

    bot = Bot(
        token=config.bot_token,
    )

    dp = setup_dispatcher()

    await dp.start_polling(
        bot,
    )


if __name__ == "__main__":

    asyncio.run(
        main(),
    )
