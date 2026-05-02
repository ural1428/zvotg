from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from app.bot.keyboards.back_menu import back_to_main_keyboard
from app.bot.keyboards.main_menu import main_menu_keyboard
from app.bot.keyboards.profile_menu import profile_keyboard, subscriptions_keyboard
from app.bot.keyboards.tariffs_menu import tariffs_keyboard
from app.bot.keyboards.subscriptions_menu import select_subscription_keyboard
from app.services.subscription_service import get_subscription_by_cer_id
from app.config import config
from app.database.session import AsyncSessionLocal
from app.integrations.mikrotik.manager import MikroTikManager
from app.services.order_service import create_order, get_order_by_id, mark_order_paid
from app.services.subscription_service import (
    get_user_subscriptions,
    get_latest_subscription,
    get_subscription_by_cer_id,
    get_subscription_days_left,
    is_subscription_active,
    create_new_pending_subscription,
    mark_cert_created,
    activate_or_extend_subscription,
    send_certificate,
)
from app.services.tariffs import TARIFFS
from sqlalchemy import select
from app.database.models import User

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
        subscriptions = await get_user_subscriptions(session, telegram_id)

    active_count = 0
    max_days_left = 0

    for subscription in subscriptions:
        if is_subscription_active(subscription):
            active_count += 1
            max_days_left = max(
                max_days_left,
                get_subscription_days_left(subscription),
            )

    return (
        "👤 Профиль\n\n"
        f"Telegram ID: `{telegram_id}`\n"
        f"Активных подписок: {active_count}\n"
        f"Всего подписок: {len(subscriptions)} / 5\n"
        f"Максимально осталось: {max_days_left} дн."
    )


async def build_subscriptions_text(telegram_id: int) -> str:
    async with AsyncSessionLocal() as session:
        subscriptions = await get_user_subscriptions(session, telegram_id)

    if not subscriptions:
        return "📦 Мои подписки\n\nУ вас пока нет подписок."

    lines = ["📦 Мои подписки\n"]

    subscriptions = [
        sub for sub in subscriptions
        if sub.status in ("paid", "sent", "expired")
    ]

    for index, subscription in enumerate(subscriptions, start=1):
        is_active = is_subscription_active(subscription)
        days_left = get_subscription_days_left(subscription)

        lines.append(
            f"\n🔐 IKEv2 VPN #{index}\n"
            f"ID сертификата: `{subscription.cer_id}`\n"
            f"Статус: {'✅ Активна' if is_active else '❌ Не активна'}\n"
            f"Осталось: {days_left} дн.\n"
            f"Сертификат: {'✅ Создан' if subscription.cert_path else '❌ Не создан'}"
        )

    return "\n".join(lines)


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
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "menu:buy")
async def menu_buy(callback: CallbackQuery):
    await callback.message.edit_text(
        "💳 Покупка подписки\n\nВыберите тариф:",
        reply_markup=tariffs_keyboard(
            action="buy",
            back_callback="menu:main",
        ),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:tariffs")
async def menu_tariffs(callback: CallbackQuery):
    await callback.message.edit_text(
        "📋 Доступные тарифы\n\nВыберите тариф для оформления заказа:",
        reply_markup=tariffs_keyboard(
            action="buy",
            back_callback="menu:main",
        ),
    )
    await callback.answer()


@router.callback_query(F.data == "subscription:renew")
async def renew_subscription(callback: CallbackQuery):
    async with AsyncSessionLocal() as session:
        subscriptions = await get_user_subscriptions(
            session=session,
            telegram_id=callback.from_user.id,
        )

    if not subscriptions:
        await callback.answer(
            "У вас нет подписок для продления.",
            show_alert=True,
        )
        return

    if len(subscriptions) == 1:
        subscription = subscriptions[0]

        await callback.message.edit_text(
            "🔄 Продление подписки\n\n"
            "Выберите тариф:",
            reply_markup=tariffs_keyboard(
                action="renew",
                cer_id=subscription.cer_id,
                back_callback="profile:subscriptions",
            ),
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        "🔄 Продление подписки\n\n"
        "Выберите подписку, которую хотите продлить:",
        reply_markup=select_subscription_keyboard(subscriptions),
    )
    await callback.answer()

@router.callback_query(F.data.startswith("renew_sub:"))
async def select_subscription_for_renew(callback: CallbackQuery):
    cer_id = callback.data.split(":", 1)[1]

    await callback.message.edit_text(
        "🔄 Продление подписки\n\n"
        f"Выбрана подписка: `{cer_id}`\n\n"
        "Теперь выберите тариф:",
        reply_markup=tariffs_keyboard(
            action="renew",
            cer_id=cer_id,
            back_callback="subscription:renew",
        ),
        parse_mode="Markdown",
    )
    await callback.answer()

@router.callback_query(F.data.startswith("tariff:"))
async def select_tariff(callback: CallbackQuery):
    parts = callback.data.split(":")
    action = parts[1]

    if action == "renew":
        cer_id = parts[2]
        tariff_code = parts[3]
    else:
        cer_id = None
        tariff_code = parts[2]

    telegram_id = callback.from_user.id

    await callback.answer("Создаю заказ...")

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            await callback.message.edit_text(
                "Пользователь не найден. Нажмите /start."
            )
            return

        if action == "buy":
            subscriptions = await get_user_subscriptions(
                session=session,
                telegram_id=telegram_id,
            )

            if len(subscriptions) >= 5:
                await callback.message.edit_text(
                    "У вас уже максимальное количество подписок: 5.",
                    reply_markup=back_to_main_keyboard,
                )
                return

            subscription = await create_new_pending_subscription(
                session=session,
                user_id=user.id,
                telegram_id=telegram_id,
            )

            order = await create_order(
                session=session,
                telegram_id=telegram_id,
                tariff_code=tariff_code,
                action="buy",
                subscription_id=subscription.id,
                cer_id=subscription.cer_id,
            )

            await callback.message.edit_text(
                "⏳ Заказ создан.\n\n"
                "Начинаем готовить сертификат..."
            )

            manager = MikroTikManager(config.mikrotik)
            cert_path = await manager.certs.create_cert(subscription.cer_id)

            subscription = await mark_cert_created(
                session=session,
                cer_id=subscription.cer_id,
                cert_path=cert_path,
            )

        elif action == "renew":
            subscription = await get_subscription_by_cer_id(
                session=session,
                cer_id=cer_id,
            )

            if not subscription or subscription.telegram_id != telegram_id:
                await callback.message.edit_text(
                    "Подписка для продления не найдена.",
                    reply_markup=back_to_main_keyboard,
                )
                return

            order = await create_order(
                session=session,
                telegram_id=telegram_id,
                tariff_code=tariff_code,
                action="renew",
                subscription_id=subscription.id,
                cer_id=subscription.cer_id,
            )

        else:
            await callback.message.edit_text(
                "Неизвестное действие.",
                reply_markup=back_to_main_keyboard,
            )
            return

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

@router.callback_query(F.data.startswith("order:test_paid:"))
async def test_paid_order(callback: CallbackQuery):
    await callback.answer("Обрабатываю оплату...")

    order_id = int(callback.data.split(":")[-1])

    async with AsyncSessionLocal() as session:
        order = await get_order_by_id(session, order_id)

        if not order:
            await callback.message.edit_text(
                "Заказ не найден.",
                reply_markup=back_to_main_keyboard,
            )
            return

        if order.status == "paid":
            await callback.message.edit_text(
                "Этот заказ уже оплачен.",
                reply_markup=back_to_main_keyboard,
            )
            return

        if not order.cer_id:
            await callback.message.edit_text(
                "У заказа не указан сертификат.",
                reply_markup=back_to_main_keyboard,
            )
            return

        subscription = await get_subscription_by_cer_id(
            session=session,
            cer_id=order.cer_id,
        )

        if not subscription:
            await callback.message.edit_text(
                "Подписка не найдена.",
                reply_markup=back_to_main_keyboard,
            )
            return

        order = await mark_order_paid(
            session=session,
            order_id=order.id,
        )

        subscription = await activate_or_extend_subscription(
            session=session,
            cer_id=order.cer_id,
            tariff_code=order.tariff_code,
        )

        if order.action == "buy":
            try:
                was_sent = await send_certificate(
                    bot=callback.bot,
                    session=session,
                    subscription=subscription,
                    force=False,
                )
            except FileNotFoundError:
                await callback.message.edit_text(
                    "✅ Оплата имитирована\n\n"
                    "Подписка активирована, но файл сертификата не найден.",
                    reply_markup=back_to_main_keyboard,
                )
                return

            if was_sent:
                text = (
                    "✅ Оплата имитирована\n\n"
                    "Подписка активирована.\n"
                    "Сертификат отправлен вам файлом."
                )
            else:
                text = (
                    "✅ Оплата имитирована\n\n"
                    "Подписка активирована.\n"
                    "Сертификат уже был отправлен ранее."
                )

        elif order.action == "renew":
            text = (
                "✅ Оплата имитирована\n\n"
                "Подписка продлена.\n"
                "Ваш сертификат остаётся прежним."
            )

        else:
            text = (
                "✅ Оплата имитирована\n\n"
                "Заказ обработан."
            )

    await callback.message.edit_text(
        text,
        reply_markup=back_to_main_keyboard,
    )

@router.callback_query(F.data == "subscription:download_cert")
async def download_cert(callback: CallbackQuery):
    async with AsyncSessionLocal() as session:
        subscription = await get_latest_subscription(
            session=session,
            telegram_id=callback.from_user.id,
        )

        if not subscription or not is_subscription_active(subscription):
            await callback.answer(
                "У вас нет активной подписки.",
                show_alert=True,
            )
            return

        try:
            await send_certificate(
                bot=callback.bot,
                session=session,
                subscription=subscription,
                force=True,
            )
        except FileNotFoundError:
            await callback.answer(
                "Файл сертификата не найден.",
                show_alert=True,
            )
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

@router.callback_query(F.data == "instruction:android")
async def instruction_android(callback: CallbackQuery):
    await callback.message.answer(
        "🤖 Инструкция для Android\n\n"
        "Здесь будет инструкция по установке IKEv2-сертификата."
    )
    await callback.answer()


@router.callback_query(F.data == "instruction:ios")
async def instruction_ios(callback: CallbackQuery):
    await callback.message.answer(
        "🍎 Инструкция для Apple iOS\n\n"
        "Здесь будет инструкция по установке IKEv2-сертификата."
    )
    await callback.answer()


@router.callback_query(F.data == "instruction:windows")
async def instruction_windows(callback: CallbackQuery):
    await callback.message.answer(
        "🪟 Инструкция для Windows\n\n"
        "Здесь будет инструкция по установке IKEv2-сертификата."
    )
    await callback.answer()


@router.callback_query(F.data == "instruction:macos")
async def instruction_macos(callback: CallbackQuery):
    await callback.message.answer(
        "💻 Инструкция для Apple MacOS\n\n"
        "Здесь будет инструкция по установке IKEv2-сертификата."
    )
    await callback.answer()
