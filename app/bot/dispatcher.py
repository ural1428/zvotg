from aiogram import (
    Dispatcher,
)

from app.bot.handlers import (
    start,
    vpn,
    profile,
    menu,
    instructions,
    easter_egg,
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

    dp.include_router(
        instructions.router,
    )

    dp.include_router(
        easter_egg.router,
    )

    return dp
