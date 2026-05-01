from aiogram.fsm.state import (
    StatesGroup,
    State,
)


class CreateVPNState(StatesGroup):

    waiting_for_cert_id = State()

    waiting_for_confirmation = State()
