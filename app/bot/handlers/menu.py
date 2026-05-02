from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from app.bot.keyboards.back_menu import back_to_main_keyboard
from app.bot.keyboards.main_menu import main_menu_keyboard
from app.bot.keyboards.profile_menu import profile_keyboard, subscriptions_keyboard
from app.bot.keyboards.tariffs_menu import tariffs_keyboard
from app.config import config
from app.database.session import AsyncSessionLocal
from app.integrations.mikrotik.manager import MikroTikManager
from app.services.order_service import create_order, get_order_by_id, mark_order_paid
from app.services.subscription_service import (
    get_latest_subscription,
    get_subscription_days_left,
    is_subscription_active,
    create_new_pending_subscription,
    mark_cert_created,
    activate_or_extend_subscription,
    send_certificate,
)
from app.services.tariffs import TARIFFS


router = Router()


WELCOME_TEXT = (
    "👋 Добро пожаловать в VPN сервис\n\n"
    "🔐 Быстрое и безопасное подключение\n"
    "🌍 Работает на всех устройствах\n\n"
    "Выберите действие:"
)


def test_payment_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Имитировать оплату",
                    callback_data=f"order:test_paid:{order_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅ Назад",
                    callback_data="menu:main",
                )
            ],
        ]
    )


async def build_profile_text(telegram_id: int) -> str:
    async with AsyncSessionLocal() as session:
        subscription = await get_latest_subscription(session, telegram_id)

    is_active = is_subscription_active(subscription)
    days_left = get_subscription_days_left(subscription)

    return (
        "👤 Профиль\n\n"
        f"Telegram ID: `{telegram_id}`\n"
        f"Подписка: {'✅ Активна' if is_active else '❌ Не активна'}\n"
        f"Осталось: {days_left if is_active else 0} дн."
    )


async def build_subscriptions_text(telegram_id: int) -> str:
    async with AsyncSessionLocal() as session:
        subscription = await get_latest_subscription(session, telegram_id)

    if not subscription:
        return "📦 Мои подписки\n\nУ вас пока нет подписок."

    is_active = is_subscription_active(subscription)
    days_left = get_subscription_days_left(subscription)

    return (
        "📦 Мои подписки\n\n"
        "🔐 IKEv2 VPN\n\n"
        f"Статус: {'✅ Активна' if is_active else '❌ Не активна'}\n"
        f"Осталось: {days_left} дн.\n"
        f"Сертификат: {'✅ Создан' if subscription.cert_path else '❌ Не создан'}"
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
        "💳 Покупка подписки\n\nВыберите тариф:",
        reply_markup=tariffs_keyboard(back_callback="menu:main"),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:tariffs")
async def menu_tariffs(callback: CallbackQuery):
    await callback.message.edit_text(
        "📋 Доступные тарифы\n\nВыберите тариф для оформления заказа:",
        reply_markup=tariffs_keyboard(back_callback="menu:main"),
    )
    await callback.answer()


@router.callback_query(F.data == "subscription:renew")
async def renew_subscription(callback: CallbackQuery):
    await callback.message.edit_text(
        "🔄 Продление подписки\n\nВыберите тариф:",
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

    tariff = TARIFFS[tariff_code]

    await callback.message.edit_text(
        "🧾 Заказ создан\n\n"
        f"Номер заказа: #{order.id}\n"
        f"Тариф: {tariff['title']}\n"
        f"Срок: {order.days} дн.\n"
        f"Сумма: {order.amount} ₽\n\n"
        "Для теста нажмите кнопку ниже.",
        reply_markup=test_payment_keyboard(order.id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("order:test_paid:"))
async def test_paid_order(callback: CallbackQuery):
    order_id = int(callback.data.split(":")[-1])
    telegram_id = callback.from_user.id

    async with AsyncSessionLocal() as session:
        order = await get_order_by_id(session, order_id)

        if not order:
            await callback.answer("Заказ не найден", show_alert=True)
            return

        if order.status == "paid":
            await callback.answer("Заказ уже оплачен", show_alert=True)
            return

        subscription = await get_latest_subscription(
            session=session,
            telegram_id=telegram_id,
        )

        if not subscription:
            subscription = await create_pending_subscription(
                session=session,
                user_id=order.user_id,
                telegram_id=telegram_id,
                cer_id=telegram_id,
                cert_path=None,
            )

        if not subscription.cert_path:
            manager = MikroTikManager(config.mikrotik)

            await callback.message.edit_text(
                "⏳ Создаю VPN-сертификат...\n\n"
                "Это может занять немного времени."
            )

            cert_path = await manager.certs.create_cert(subscription.cer_id)

            subscription = await mark_cert_created(
                session=session,
                cer_id=telegram_id,
                cert_path=cert_path,
            )

        order = await mark_order_paid(session, order_id)

        subscription = await activate_or_extend_subscription(
            session=session,
            cer_id=telegram_id,
            tariff_code=order.tariff_code,
        )

        was_sent = await send_certificate(
            bot=callback.bot,
            session=session,
            subscription=subscription,
            force=False,
        )

    if was_sent:
        text = (
            "✅ Оплата имитирована\n\n"
            "Подписка активирована.\n"
            "Сертификат отправлен вам файлом."
        )
    else:
        text = (
            "✅ Оплата имитирована\n\n"
            "Подписка продлена.\n"
            "Ваш сертификат остаётся прежним."
        )

    await callback.message.edit_text(
        text,
        reply_markup=back_to_main_keyboard,
    )
    await callback.answer()


@router.callback_query(F.data == "subscription:download_cert")
async def download_cert(callback: CallbackQuery):
    async with AsyncSessionLocal() as session:
        subscription = await get_latest_subscription(
            session=session,
            telegram_id=callback.from_user.id,
        )

        if not subscription or not is_subscription_active(subscription):
            await callback.answer("У вас нет активной подписки.", show_alert=True)
            return

        try:
            await send_certificate(
                bot=callback.bot,
                session=session,
                subscription=subscription,
                force=True,
            )
        except FileNotFoundError:
            await callback.answer("Файл сертификата не найден.", show_alert=True)
            return

    await callback.answer("Сертификат отправлен.", show_alert=True)


@router.callback_query(F.data.startswith("order:pay:"))
async def pay_order(callback: CallbackQuery):
    order_id = int(callback.data.split(":")[-1])

    await callback.message.edit_text(
        "💳 Оплата заказа\n\n"
        f"Заказ #{order_id}\n\n"
        "Здесь позже будет подключение платёжной системы.",
        reply_markup=back_to_main_keyboard,
    )
    await callback.answer()
