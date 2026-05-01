from aiogram import (
    Router,
    F,
)

from aiogram.types import (
    Message,
)

from aiogram.fsm.context import (
    FSMContext,
)

from app.bot.states.vpn import (
    CreateVPNState,
)

router = Router()


@router.message(
    F.text == "Создать VPN"
)
async def create_vpn_start(
    message: Message,
    state: FSMContext,
):

    await state.set_state(
        CreateVPNState.waiting_for_cert_id,
    )

    await message.answer(
        "Введите cert_id",
    )


@router.message(
    CreateVPNState.waiting_for_cert_id,
)
async def process_cert_id(
    message: Message,
    state: FSMContext,
):

    cert_id = message.text

    await state.update_data(
        cert_id=cert_id,
    )

    await state.set_state(
        CreateVPNState.waiting_for_confirmation,
    )

    await message.answer(
        f"Создать сертификат {cert_id}? (yes/no)"
    )


@router.message(
    CreateVPNState.waiting_for_confirmation,
)
async def confirm_create(
    message: Message,
    state: FSMContext,
):

    if message.text.lower() != "yes":

        await state.clear()

        return await message.answer(
            "Отменено",
        )

    data = await state.get_data()

    cert_id = int(
        data["cert_id"]
    )

    await message.answer(
        "Создаю сертификат...",
    )

    """
    Тут будет вызов VPNService
    """

    await message.answer(
        f"Сертификат {cert_id} создан",
    )

    await state.clear()
