from aiogram import (
    Dispatcher,
)

from app.bot.handlers import (
    start,
    vpn,
)


def setup_dispatcher():

    dp = Dispatcher()

    dp.include_router(
        start.router,
    )

    dp.include_router(
        vpn.router,
    )

    return dp
