import re

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from sqlalchemy import select

from app.bot.keyboards.back_menu import back_to_main_keyboard
from app.bot.keyboards.main_menu import main_menu_keyboard
from app.bot.keyboards.profile_menu import profile_keyboard, subscriptions_keyboard
from app.bot.keyboards.subscriptions_menu import (
    select_subscription_keyboard,
    select_subscription_for_download_keyboard,
)
from app.bot.keyboards.tariffs_menu import tariffs_keyboard
from app.config import config
from app.database.models import User
from app.database.session import AsyncSessionLocal
from app.integrations.mikrotik.manager import MikroTikManager
from app.services.order_service import (
    create_order,
    get_order_by_id,
    mark_order_paid,
    attach_payment_to_order,
)
from app.services.tbank_service import init_tbank_payment
from app.services.subscription_service import (
    get_user_subscriptions,
    get_subscription_by_cer_id,
    get_subscription_days_left,
    is_subscription_active,
    create_new_pending_subscription,
    mark_cert_created,
    activate_or_extend_subscription,
    send_certificate,
    send_p12_file,
    has_lifetime_subscription,
)
from app.services.referral_service import (
    build_referral_code,
    get_referral_stats,
    reward_referrer_for_paid_user,
)
from app.services.tariffs import TARIFFS


router = Router()

VISIBLE_SUBSCRIPTION_STATUSES = ("paid", "sent", "expired")

WELCOME_TEXT = (
    "👋 Добро пожаловать в сервис\n\n"
    "🔐 Быстрое и безопасное подключение\n"
    "🌍 Работает на всех устройствах\n\n"
    "Выберите действие:"
)

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


class OrderEmailState(StatesGroup):
    waiting_email = State()


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_RE.match(email.strip()))


def visible_subscriptions(subscriptions):
    return [
        sub for sub in subscriptions
        if sub.status in VISIBLE_SUBSCRIPTION_STATUSES
    ]


def payment_keyboard(payment_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💳 Оплатить",
                    url=payment_url,
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


def support_bot_url() -> str:
    username = getattr(config, "support_bot_username", None)

    if username:
        return f"https://t.me/{username}"

    return "https://t.me/support"


def support_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🤖 Android — быстрая установка",
                    callback_data="vpn:android_setup",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🍎 Apple iOS — установка VPN",
                    callback_data="vpn:ios_setup",
                )
            ],
            [
                InlineKeyboardButton(
                    text="💬 Написать в поддержку",
                    url=support_bot_url(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅ Назад",
                    callback_data="menu:profile",
                )
            ],
        ]
    )


async def build_profile_text(telegram_id: int) -> str:
    async with AsyncSessionLocal() as session:
        subscriptions = await get_user_subscriptions(session, telegram_id)

    subscriptions = visible_subscriptions(subscriptions)

    active_count = 0
    max_days_left = 0
    is_lifetime = has_lifetime_subscription(subscriptions)

    for subscription in subscriptions:
        if is_subscription_active(subscription):
            active_count += 1
            max_days_left = max(
                max_days_left,
                get_subscription_days_left(subscription),
            )

    crown = " 👑" if is_lifetime else ""
    days_text = "до 2100 года" if is_lifetime else f"{max_days_left} дн."

    return (
        f"👤 Профиль{crown}\n\n"
        f"Telegram ID: `{telegram_id}`\n"
        f"Активных подписок: {active_count}\n"
        f"Всего подписок: {len(subscriptions)} / 5\n"
        f"Максимально осталось: {days_text}"
    )


async def build_subscriptions_text(telegram_id: int) -> str:
    async with AsyncSessionLocal() as session:
        subscriptions = await get_user_subscriptions(session, telegram_id)

    subscriptions = visible_subscriptions(subscriptions)

    if not subscriptions:
        return "📦 Мои подписки\n\nУ вас пока нет активных или завершённых подписок."

    lines = ["📦 Мои подписки\n"]

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


async def show_referral_message(message: Message):
    bot_info = await message.bot.get_me()

    referral_code = build_referral_code(message.from_user.id)
    referral_link = f"https://t.me/{bot_info.username}?start={referral_code}"

    async with AsyncSessionLocal() as session:
        stats = await get_referral_stats(
            session=session,
            telegram_id=message.from_user.id,
        )

    await message.answer(
        "🎁 Получить 5 дней бесплатно\n\n"
        "Пригласите друга по вашей ссылке.\n"
        "Когда он оплатит подписку, вы получите +5 дней к вашей подписке.\n\n"
        f"Ваша ссылка:\n`{referral_link}`\n\n"
        f"Приглашено: {stats['total']}\n"
        f"Ожидают оплату: {stats['registered']}\n"
        f"Бонусов начислено: {stats['rewarded']}",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="⬅ Назад",
                        callback_data="menu:profile",
                    )
                ]
            ]
        ),
        parse_mode="Markdown",
    )


@router.callback_query(F.data == "menu:main")
async def menu_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()

    await callback.message.edit_text(
        WELCOME_TEXT,
        reply_markup=main_menu_keyboard(callback.from_user.id),
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
    async with AsyncSessionLocal() as session:
        subscriptions = await get_user_subscriptions(
            session=session,
            telegram_id=callback.from_user.id,
        )

    subscriptions = visible_subscriptions(subscriptions)
    text = await build_subscriptions_text(callback.from_user.id)

    await callback.message.edit_text(
        text,
        reply_markup=subscriptions_keyboard(
            has_subscriptions=bool(subscriptions),
        ),
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

    subscriptions = visible_subscriptions(subscriptions)

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
async def select_tariff(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    action = parts[1]

    if action == "renew":
        cer_id = parts[2]
        tariff_code = parts[3]
    else:
        cer_id = None
        tariff_code = parts[2]

    await state.set_state(OrderEmailState.waiting_email)
    await state.update_data(
        action=action,
        cer_id=cer_id,
        tariff_code=tariff_code,
    )

    await callback.message.edit_text(
        "📧 Введите email для отправки чека.\n\n"
        "Например:\n"
        "`user@example.com`",
        parse_mode="Markdown",
        reply_markup=back_to_main_keyboard,
    )

    await callback.answer()


@router.message(OrderEmailState.waiting_email)
async def process_order_email(message: Message, state: FSMContext):
    if not message.text:
        await message.answer(
            "Введите email текстом, например:\n"
            "`user@example.com`",
            parse_mode="Markdown",
        )
        return

    text = message.text.strip()

    if text in {"Главное меню", "Профиль", "Тарифы", "Поддержка"}:
        await state.clear()

        if text == "Главное меню":
            await message.answer(
                WELCOME_TEXT,
                reply_markup=main_menu_keyboard(message.from_user.id),
            )
            return

        if text == "Профиль":
            profile_text = await build_profile_text(message.from_user.id)
            await message.answer(
                profile_text,
                reply_markup=profile_keyboard,
                parse_mode="Markdown",
            )
            return

        if text == "Тарифы":
            await message.answer(
                "📋 Доступные тарифы\n\n"
                "Выберите тариф для оформления заказа:",
                reply_markup=tariffs_keyboard(
                    action="buy",
                    back_callback="menu:main",
                ),
            )
            return

        if text == "Поддержка":
            await message.answer(
                "🛠 Управление VPN\n\n"
                "Для настройки вашего устройства воспользуйтесь инструкциями ниже "
                "или обратитесь в поддержку.",
                reply_markup=support_keyboard(),
            )
            return

    email = text.lower()

    if not is_valid_email(email):
        await message.answer(
            "Некорректный email.\n\n"
            "Введите email ещё раз, например:\n"
            "`user@example.com`",
            parse_mode="Markdown",
        )
        return

    data = await state.get_data()
    await state.clear()

    await create_payment_after_email(
        message=message,
        action=data["action"],
        tariff_code=data["tariff_code"],
        cer_id=data.get("cer_id"),
        customer_email=email,
    )


async def create_payment_after_email(
    message: Message,
    action: str,
    tariff_code: str,
    cer_id: str | None,
    customer_email: str,
):
    telegram_id = message.from_user.id

    status_message = await message.answer("⏳ Создаю заказ...")

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            await status_message.edit_text(
                "Пользователь не найден. Нажмите /start.",
                reply_markup=back_to_main_keyboard,
            )
            return

        if action == "buy":
            subscriptions = await get_user_subscriptions(
                session=session,
                telegram_id=telegram_id,
            )

            visible_count = len(visible_subscriptions(subscriptions))

            if visible_count >= 5:
                await status_message.edit_text(
                    "У вас уже максимальное количество подписок: 5.",
                    reply_markup=back_to_main_keyboard,
                )
                return

            try:
                subscription = await create_new_pending_subscription(
                    session=session,
                    user_id=user.id,
                    telegram_id=telegram_id,
                )
            except ValueError:
                await status_message.edit_text(
                    "У вас уже есть 5 созданных подписок.\n\n"
                    "Если часть заказов не была оплачена, обратитесь в поддержку.",
                    reply_markup=back_to_main_keyboard,
                )
                return

            order = await create_order(
                session=session,
                telegram_id=telegram_id,
                tariff_code=tariff_code,
                action="buy",
                subscription_id=subscription.id,
                cer_id=subscription.cer_id,
                customer_email=customer_email,
            )

            await status_message.edit_text(
                "⏳ Заказ создан.\n\n"
                "Подготавливаю данные для подключения..."
            )

            try:
                manager = MikroTikManager(config.mikrotik)
                cert_path = await manager.certs.create_cert(subscription.cer_id)

                subscription = await mark_cert_created(
                    session=session,
                    cer_id=subscription.cer_id,
                    cert_path=cert_path,
                )
            except Exception as error:
                await status_message.edit_text(
                    "Не удалось подготовить данные для подключения.\n\n"
                    "Попробуйте позже или обратитесь в поддержку.",
                    reply_markup=back_to_main_keyboard,
                )
                raise error

        elif action == "renew":
            subscription = await get_subscription_by_cer_id(
                session=session,
                cer_id=cer_id,
            )

            if (
                not subscription
                or subscription.telegram_id != telegram_id
                or subscription.status not in VISIBLE_SUBSCRIPTION_STATUSES
            ):
                await status_message.edit_text(
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
                customer_email=customer_email,
            )

        else:
            await status_message.edit_text(
                "Неизвестное действие.",
                reply_markup=back_to_main_keyboard,
            )
            return

        try:
            payment_data = await init_tbank_payment(order)
        except Exception as error:
            await status_message.edit_text(
                "Не удалось создать ссылку на оплату.\n\n"
                "Попробуйте позже или обратитесь в поддержку.",
                reply_markup=back_to_main_keyboard,
            )
            raise error

        payment_url = payment_data.get("PaymentURL")

        if not payment_url:
            await status_message.edit_text(
                "Банк не вернул ссылку на оплату.\n\n"
                "Попробуйте позже или обратитесь в поддержку.",
                reply_markup=back_to_main_keyboard,
            )
            return

        order = await attach_payment_to_order(
            session=session,
            order_id=order.id,
            payment_id=str(payment_data.get("PaymentId")),
            payment_url=payment_url,
            payment_status=payment_data.get("Status"),
        )

    tariff = TARIFFS[tariff_code]
    order_number = order.public_order_id or order.id

    await status_message.edit_text(
        "🧾 Заказ создан\n\n"
        f"Номер заказа: #{order_number}\n"
        f"Тариф: {tariff['title']}\n"
        f"Срок: {order.days} дн.\n"
        f"Сумма: {order.amount} ₽\n"
        f"Email для чека: `{order.customer_email}`\n\n"
        "Нажмите кнопку ниже для оплаты.",
        reply_markup=payment_keyboard(order.payment_url),
        parse_mode="Markdown",
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

        await reward_referrer_for_paid_user(
            session=session,
            referred_telegram_id=order.telegram_id,
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
async def download_cert_menu(callback: CallbackQuery):
    async with AsyncSessionLocal() as session:
        subscriptions = await get_user_subscriptions(
            session=session,
            telegram_id=callback.from_user.id,
        )

        subscriptions = [
            sub for sub in subscriptions
            if sub.status in ("paid", "sent") and is_subscription_active(sub)
        ]

        if not subscriptions:
            await callback.answer(
                "У вас нет активных подписок.",
                show_alert=True,
            )
            return

        if len(subscriptions) == 1:
            subscription = subscriptions[0]

            try:
                await send_p12_file(
                    bot=callback.bot,
                    subscription=subscription,
                )
            except FileNotFoundError:
                await callback.answer(
                    "Файл сертификата не найден на сервере.",
                    show_alert=True,
                )
                return

            await callback.answer("Сертификат отправлен.", show_alert=True)
            return

    await callback.message.edit_text(
        "📄 Скачать сертификат\n\n"
        "Выберите подписку:",
        reply_markup=select_subscription_for_download_keyboard(subscriptions),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("download_cert:"))
async def download_selected_cert(callback: CallbackQuery):
    cer_id = callback.data.split(":", 1)[1]

    async with AsyncSessionLocal() as session:
        subscription = await get_subscription_by_cer_id(
            session=session,
            cer_id=cer_id,
        )

        if (
            not subscription
            or subscription.telegram_id != callback.from_user.id
            or subscription.status not in ("paid", "sent")
            or not is_subscription_active(subscription)
        ):
            await callback.answer(
                "Подписка не найдена или не активна.",
                show_alert=True,
            )
            return

        try:
            await send_p12_file(
                bot=callback.bot,
                subscription=subscription,
            )
        except FileNotFoundError:
            await callback.answer(
                "Файл сертификата не найден на сервере.",
                show_alert=True,
            )
            return

    await callback.answer("Сертификат отправлен.", show_alert=True)


@router.callback_query(F.data.startswith("order:pay:"))
async def pay_order(callback: CallbackQuery):
    await callback.answer()

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

        if not order.customer_email:
            await callback.message.edit_text(
                "Для оплаты требуется email для отправки чека.\n\n"
                "Пожалуйста, создайте заказ заново.",
                reply_markup=back_to_main_keyboard,
            )
            return

        if not order.payment_url:
            try:
                payment_data = await init_tbank_payment(order)
            except Exception as error:
                await callback.message.edit_text(
                    "Не удалось создать ссылку на оплату.\n\n"
                    "Попробуйте позже или обратитесь в поддержку.",
                    reply_markup=back_to_main_keyboard,
                )
                raise error

            order = await attach_payment_to_order(
                session=session,
                order_id=order.id,
                payment_id=str(payment_data.get("PaymentId")),
                payment_url=payment_data.get("PaymentURL"),
                payment_status=payment_data.get("Status"),
            )

    order_number = order.public_order_id or order.id

    await callback.message.edit_text(
        "💳 Оплата заказа\n\n"
        f"Заказ #{order_number}\n"
        f"Сумма: {order.amount} ₽\n"
        f"Email для чека: `{order.customer_email}`\n\n"
        "Нажмите кнопку ниже для оплаты.",
        reply_markup=payment_keyboard(order.payment_url),
        parse_mode="Markdown",
    )


@router.callback_query(F.data == "menu:support")
async def menu_support(callback: CallbackQuery):
    try:
        await callback.answer()
    except TelegramBadRequest:
        pass

    try:
        await callback.message.edit_text(
            "🛠 Управление VPN\n\n"
            "Для настройки вашего устройства воспользуйтесь инструкциями ниже "
            "или обратитесь в поддержку.",
            reply_markup=support_keyboard(),
        )
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise


@router.callback_query(F.data == "vpn:android_setup")
async def vpn_android_setup(callback: CallbackQuery):
    async with AsyncSessionLocal() as session:
        subscriptions = await get_user_subscriptions(
            session=session,
            telegram_id=callback.from_user.id,
        )

    subscriptions = [
        sub for sub in subscriptions
        if sub.status in ("paid", "sent") and is_subscription_active(sub)
    ]

    if not subscriptions:
        await callback.answer(
            "У вас нет активных подписок.",
            show_alert=True,
        )
        return

    if len(subscriptions) == 1:
        subscription = subscriptions[0]

        await callback.message.edit_text(
            "🤖 Быстрая установка VPN на Android\n\n"
            "1. Скачайте [StrongSwan из Google Play]"
            "(https://play.google.com/store/apps/details?id=org.strongswan.android) "
            "или скачайте APK файл по кнопке ниже.\n\n"
            "2. Нажмите *«Загрузить профиль»*.\n\n"
            "3. Введите пароль: `123456789`.\n\n"
            "4. Два раза нажмите *OK*.\n\n"
            "5. Выберите *«Выбрать»*. Чек-бокс уже будет стоять на вашем сертификате.\n\n"
            "6. Нажмите *IMPORT* в правом верхнем углу.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="📦 Скачать APK StrongSwan",
                            callback_data="android:download_apk",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="⚡ Загрузить профиль",
                            callback_data=f"android:download_profile:{subscription.cer_id}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="🎥 Видео-инструкция",
                            callback_data="android:video",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="⬅ Назад",
                            callback_data="menu:support",
                        )
                    ],
                ]
            ),
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )
        await callback.answer()
        return

    keyboard = []

    for index, subscription in enumerate(subscriptions, start=1):
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"🔐 IKEv2 VPN #{index}",
                    callback_data=f"android_setup:{subscription.cer_id}",
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                text="⬅ Назад",
                callback_data="menu:support",
            )
        ]
    )

    await callback.message.edit_text(
        "🤖 Быстрая установка Android\n\n"
        "Выберите подписку:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
    )
    await callback.answer()


@router.callback_query(F.data == "vpn:ios_setup")
async def vpn_ios_setup(callback: CallbackQuery):
    async with AsyncSessionLocal() as session:
        subscriptions = await get_user_subscriptions(
            session=session,
            telegram_id=callback.from_user.id,
        )

    subscriptions = [
        sub for sub in subscriptions
        if sub.status in ("paid", "sent") and is_subscription_active(sub)
    ]

    if not subscriptions:
        await callback.answer("У вас нет активных подписок.", show_alert=True)
        return

    if len(subscriptions) == 1:
        await callback.message.edit_text(
            "🍎 Apple iOS — установка VPN",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="Открыть инструкцию iOS",
                            callback_data=f"ios_setup:{subscriptions[0].cer_id}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="⬅ Назад",
                            callback_data="menu:support",
                        )
                    ],
                ]
            ),
        )
        await callback.answer()
        return

    keyboard = []

    for index, subscription in enumerate(subscriptions, start=1):
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"🔐 IKEv2 VPN #{index}",
                    callback_data=f"ios_setup:{subscription.cer_id}",
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                text="⬅ Назад",
                callback_data="menu:support",
            )
        ]
    )

    await callback.message.edit_text(
        "🍎 Apple iOS — установка VPN\n\nВыберите подписку:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
    )
    await callback.answer()


@router.callback_query(F.data == "profile:referral")
async def profile_referral(callback: CallbackQuery):
    bot_info = await callback.bot.get_me()

    referral_code = build_referral_code(callback.from_user.id)
    referral_link = f"https://t.me/{bot_info.username}?start={referral_code}"

    async with AsyncSessionLocal() as session:
        stats = await get_referral_stats(
            session=session,
            telegram_id=callback.from_user.id,
        )

    await callback.message.edit_text(
        "🎁 Получить 5 дней бесплатно\n\n"
        "Пригласите друга по вашей ссылке.\n"
        "Когда он оплатит подписку, вы получите +5 дней к вашей подписке.\n\n"
        f"Ваша ссылка:\n`{referral_link}`\n\n"
        f"Приглашено: {stats['total']}\n"
        f"Ожидают оплату: {stats['registered']}\n"
        f"Бонусов начислено: {stats['rewarded']}",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="⬅ Назад",
                        callback_data="menu:profile",
                    )
                ]
            ]
        ),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.message(F.text == "Главное меню")
async def reply_main_menu(message: Message):
    await message.answer(
        WELCOME_TEXT,
        reply_markup=main_menu_keyboard(message.from_user.id),
    )


@router.message(F.text == "Профиль")
async def reply_profile(message: Message):
    text = await build_profile_text(message.from_user.id)

    await message.answer(
        text,
        reply_markup=profile_keyboard,
        parse_mode="Markdown",
    )


@router.message(F.text == "Тарифы")
async def reply_tariffs(message: Message):
    await message.answer(
        "📋 Доступные тарифы\n\n"
        "Выберите тариф для оформления заказа:",
        reply_markup=tariffs_keyboard(
            action="buy",
            back_callback="menu:main",
        ),
    )


@router.message(F.text == "Поддержка")
async def reply_support(message: Message):
    await message.answer(
        "🛠 Управление VPN\n\n"
        "Для настройки вашего устройства воспользуйтесь инструкциями ниже "
        "или обратитесь в поддержку.",
        reply_markup=support_keyboard(),
    )