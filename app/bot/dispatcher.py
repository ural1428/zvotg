from aiogram import (
    Dispatcher,
)

from app.bot.handlers import (
    start,
    vpn,
    profile,
    menu,
)


def setup_dispatcher():

    dp = Dispatcher()

    dp.include_router(
        start.router,
    )

    dp.include_router(
        vpn.router,
    )

    dp.include_router(
        profile.router,
    )

    dp.include_router(
        menu.router,
    )

    return dp
