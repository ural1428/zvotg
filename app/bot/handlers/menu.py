from aiogram import Router, F
from aiogram.types import CallbackQuery

from app.bot.keyboards.back_menu import back_to_main_keyboard
from app.bot.keyboards.main_menu import main_menu_keyboard
from app.bot.keyboards.profile_menu import profile_keyboard, subscriptions_keyboard
from app.database.session import AsyncSessionLocal
from app.bot.keyboards.tariffs_menu import tariffs_keyboard
from app.services.order_service import create_order
from app.services.subscription_service import (
    get_latest_subscription,
    get_subscription_days_left,
    is_subscription_active,
)

router = Router()


WELCOME_TEXT = (
    "👋 Добро пожаловать в VPN сервис\n\n"
    "🔐 Быстрое и безопасное подключение\n"
    "🌍 Работает на всех устройствах\n\n"
    "Выберите действие:"
)


async def build_profile_text(telegram_id: int) -> str:
    async with AsyncSessionLocal() as session:
        subscription = await get_latest_subscription(
            session=session,
            telegram_id=telegram_id,
        )

    is_active = is_subscription_active(subscription)
    days_left = get_subscription_days_left(subscription)

    status_text = "✅ Активна" if is_active else "❌ Не активна"
    days_text = f"{days_left} дн." if is_active else "0 дн."

    return (
        "👤 Профиль\n\n"
        f"Telegram ID: `{telegram_id}`\n"
        f"Подписка: {status_text}\n"
        f"Осталось: {days_text}"
    )


async def build_subscriptions_text(telegram_id: int) -> str:
    async with AsyncSessionLocal() as session:
        subscription = await get_latest_subscription(
            session=session,
            telegram_id=telegram_id,
        )

    if not subscription:
        return (
            "📦 Мои подписки\n\n"
            "У вас пока нет подписок."
        )

    is_active = is_subscription_active(subscription)
    days_left = get_subscription_days_left(subscription)

    status_text = "✅ Активна" if is_active else "❌ Не активна"

    cert_status = "✅ Создан" if subscription.cert_path else "❌ Не создан"

    return (
        "📦 Мои подписки\n\n"
        "🔐 IKEv2 VPN\n\n"
        f"Статус: {status_text}\n"
        f"Осталось: {days_left} дн.\n"
        f"Сертификат: {cert_status}"
    )


@router.callback_query(F.data == "menu:main")
async def menu_main(callback: CallbackQuery):
    await callback.message.edit_text(
        WELCOME_TEXT,
        reply_markup=main_menu_keyboard,
    )
    await callback.answer()


@router.callback_query(F.data == "menu:profile")
async def menu_profile(callback: CallbackQuery):
    text = await build_profile_text(callback.from_user.id)

    await callback.message.edit_text(
        text,
        reply_markup=profile_keyboard,
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "profile:subscriptions")
async def profile_subscriptions(callback: CallbackQuery):
    text = await build_subscriptions_text(callback.from_user.id)

    await callback.message.edit_text(
        text,
        reply_markup=subscriptions_keyboard,
    )
    await callback.answer()


@router.callback_query(F.data == "menu:buy")
async def menu_buy(callback: CallbackQuery):
    await callback.message.edit_text(
        "💳 Покупка подписки\n\n"
        "Выберите тариф:",
        reply_markup=tariffs_keyboard(back_callback="menu:main"),
    )
    await callback.answer()

@router.callback_query(F.data == "menu:tariffs")
async def menu_tariffs(callback: CallbackQuery):
    await callback.message.edit_text(
        "📋 Доступные тарифы\n\n"
        "Выберите тариф для оформления заказа:",
        reply_markup=tariffs_keyboard(back_callback="menu:main"),
    )
    await callback.answer()

@router.callback_query(F.data == "subscription:renew")
async def renew_subscription(callback: CallbackQuery):
    await callback.message.edit_text(
        "🔄 Продление подписки\n\n"
        "Выберите тариф:",
        reply_markup=tariffs_keyboard(back_callback="profile:subscriptions"),
    )
    await callback.answer()

@router.callback_query(F.data.startswith("tariff:select:"))
async def select_tariff(callback: CallbackQuery):
    tariff_code = callback.data.split(":")[-1]

    async with AsyncSessionLocal() as session:
        order = await create_order(
            session=session,
            telegram_id=callback.from_user.id,
            tariff_code=tariff_code,
        )

    await callback.message.edit_text(
        "🧾 Заказ создан\n\n"
        f"Номер заказа: #{order.id}\n"
        f"Тариф: {tariff_code}\n"
        f"Срок: {order.days} дн.\n"
        f"Сумма: {order.amount} ₽\n\n"
        "Следующим шагом здесь будет оплата.",
        reply_markup=back_to_main_keyboard,
    )

    await callback.answer()

@router.callback_query(F.data == "subscription:download_cert")
async def download_cert(callback: CallbackQuery):
    await callback.answer(
        "Скачивание сертификата добавим следующим шагом.",
        show_alert=True,
    )
@router.callback_query(F.data.startswith("order:pay:"))
async def pay_order(callback: CallbackQuery):
    order_id = int(callback.data.split(":")[-1])

    await callback.message.edit_text(
        "💳 Оплата заказа\n\n"
        f"Заказ #{order_id}\n\n"
        "Здесь будет подключение платёжной системы."
    )

    await callback.answer()
