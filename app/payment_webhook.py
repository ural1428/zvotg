import re
from aiohttp import web
from aiogram import Bot
from sqlalchemy import select

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
from app.services.subscription_service import (
    activate_or_extend_subscription,
    get_subscription_by_cer_id,
    get_user_subscriptions,
    get_subscription_days_left,
    is_subscription_active,
    create_new_pending_subscription,
    mark_cert_created,
    send_certificate,
)
from app.services.referral_service import reward_referrer_for_paid_user
from app.services.tariffs import TARIFFS
from app.services.tbank_service import (
    init_tbank_payment,
    verify_tbank_notification,
)
from app.services.webapp_auth import (
    validate_telegram_init_data,
    WebAppAuthError,
)


async def handle_successful_payment(bot: Bot, order_id: int):
    async with AsyncSessionLocal() as session:
        order = await get_order_by_id(session, order_id)

        if not order:
            return

        if order.status == "paid":
            return

        if not order.cer_id:
            return

        subscription = await get_subscription_by_cer_id(
            session=session,
            cer_id=order.cer_id,
        )

        if not subscription:
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
            await send_certificate(
                bot=bot,
                session=session,
                subscription=subscription,
                force=False,
            )

            await bot.send_message(
                chat_id=order.telegram_id,
                text=(
                    "✅ Оплата прошла успешно!\n\n"
                    "Подписка активирована."
                ),
            )

        elif order.action == "renew":
            await bot.send_message(
                chat_id=order.telegram_id,
                text=(
                    "✅ Оплата прошла успешно!\n\n"
                    "Подписка продлена. Ваш сертификат остаётся прежним."
                ),
            )


def parse_order_id(order_id_raw: str) -> int | None:
    prefix = f"{config.payment_project_code}-"

    if not order_id_raw.startswith(prefix):
        return None

    payload = order_id_raw.replace(prefix, "", 1)

    try:
        return int(payload.split("-")[0])
    except ValueError:
        return None


async def tbank_webhook(request: web.Request):
    data = await request.json()

    if not verify_tbank_notification(data):
        return web.Response(text="INVALID TOKEN", status=403)

    status = data.get("Status")
    order_id_raw = str(data.get("OrderId", ""))

    order_id = parse_order_id(order_id_raw)

    if not order_id:
        return web.Response(text="UNKNOWN ORDER", status=400)

    if status == "CONFIRMED":
        bot = Bot(token=config.bot_token)

        try:
            await handle_successful_payment(bot, order_id)
        finally:
            await bot.session.close()

    return web.Response(text="OK")


async def payment_success(request: web.Request):
    bot_username = config.bot_username

    html = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Готово</title>

        <style>
            * {{
                box-sizing: border-box;
            }}

            body {{
                margin: 0;
                padding: 20px;
                min-height: 100vh;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
                background: linear-gradient(180deg, #f3f7ff 0%, #ffffff 100%);
                color: #111827;
                display: flex;
                align-items: center;
                justify-content: center;
            }}

            .card {{
                width: 100%;
                max-width: 420px;
                background: #ffffff;
                border-radius: 24px;
                padding: 32px 24px;
                text-align: center;
                box-shadow: 0 16px 40px rgba(15, 23, 42, 0.10);
            }}

            .icon {{
                width: 72px;
                height: 72px;
                border-radius: 50%;
                background: #dcfce7;
                color: #16a34a;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 20px;
                font-size: 38px;
                font-weight: 700;
            }}

            h1 {{
                margin: 0 0 10px;
                font-size: 26px;
                line-height: 1.2;
                font-weight: 700;
            }}

            p {{
                margin: 0 0 28px;
                color: #6b7280;
                font-size: 16px;
                line-height: 1.5;
            }}

            .button {{
                display: block;
                width: 100%;
                padding: 16px 20px;
                border-radius: 16px;
                background: #229ED9;
                color: #ffffff;
                text-decoration: none;
                font-size: 17px;
                font-weight: 700;
                box-shadow: 0 10px 24px rgba(34, 158, 217, 0.28);
            }}

            .button:active {{
                transform: scale(0.98);
            }}

            .hint {{
                margin-top: 16px;
                font-size: 13px;
                color: #9ca3af;
            }}
        </style>
    </head>

    <body>
        <div class="card">
            <div class="icon">✓</div>

            <h1>Готово</h1>

            <p>
                Оплата успешно выполнена.<br>
                Доступ активируется автоматически.
            </p>

            <a class="button" href="tg://resolve?domain={bot_username}">
                Вернуться
            </a>

            <div class="hint">
                Нажмите кнопку, чтобы вернуться в Telegram
            </div>
        </div>
    </body>
    </html>
    """

    return web.Response(
        text=html,
        content_type="text/html",
    )


async def payment_fail(request: web.Request):
    bot_username = config.bot_username

    html = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Оплата не завершена</title>

        <style>
            * {{
                box-sizing: border-box;
            }}

            body {{
                margin: 0;
                padding: 20px;
                min-height: 100vh;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
                background: linear-gradient(180deg, #fff7ed 0%, #ffffff 100%);
                color: #111827;
                display: flex;
                align-items: center;
                justify-content: center;
            }}

            .card {{
                width: 100%;
                max-width: 420px;
                background: #ffffff;
                border-radius: 24px;
                padding: 32px 24px;
                text-align: center;
                box-shadow: 0 16px 40px rgba(15, 23, 42, 0.10);
            }}

            .icon {{
                width: 72px;
                height: 72px;
                border-radius: 50%;
                background: #fee2e2;
                color: #dc2626;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 20px;
                font-size: 38px;
                font-weight: 700;
            }}

            h1 {{
                margin: 0 0 10px;
                font-size: 26px;
                line-height: 1.2;
                font-weight: 700;
            }}

            p {{
                margin: 0 0 28px;
                color: #6b7280;
                font-size: 16px;
                line-height: 1.5;
            }}

            .button {{
                display: block;
                width: 100%;
                padding: 16px 20px;
                border-radius: 16px;
                background: #229ED9;
                color: #ffffff;
                text-decoration: none;
                font-size: 17px;
                font-weight: 700;
            }}
        </style>
    </head>

    <body>
        <div class="card">
            <div class="icon">!</div>

            <h1>Оплата не завершена</h1>

            <p>
                Попробуйте ещё раз или вернитесь в Telegram.
            </p>

            <a class="button" href="tg://resolve?domain={bot_username}">
                Вернуться
            </a>
        </div>
    </body>
    </html>
    """

    return web.Response(
        text=html,
        content_type="text/html",
    )

VISIBLE_SUBSCRIPTION_STATUSES = ("paid", "sent", "expired")

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_RE.match(email.strip()))


def get_init_data_from_request(request: web.Request) -> str:
    return request.headers.get("X-Telegram-Init-Data", "")


def visible_subscriptions(subscriptions):
    return [
        subscription
        for subscription in subscriptions
        if subscription.status in VISIBLE_SUBSCRIPTION_STATUSES
    ]


async def get_webapp_user(request: web.Request) -> dict:
    init_data = get_init_data_from_request(request)
    return validate_telegram_init_data(init_data)


async def webapp_profile(request: web.Request):
    try:
        auth = await get_webapp_user(request)
    except WebAppAuthError as error:
        return web.json_response(
            {"ok": False, "error": str(error)},
            status=401,
        )

    telegram_id = auth["telegram_id"]

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            return web.json_response(
                {
                    "ok": False,
                    "error": "user_not_found",
                    "message": "Сначала нажмите /start в боте.",
                },
                status=404,
            )

        subscriptions = await get_user_subscriptions(
            session=session,
            telegram_id=telegram_id,
        )

    subscriptions = visible_subscriptions(subscriptions)

    active_count = 0
    max_days_left = 0
    subscription_items = []

    for index, subscription in enumerate(subscriptions, start=1):
        active = is_subscription_active(subscription)
        days_left = get_subscription_days_left(subscription)

        if active:
            active_count += 1
            max_days_left = max(max_days_left, days_left)

        subscription_items.append(
            {
                "id": subscription.id,
                "index": index,
                "cer_id": subscription.cer_id,
                "status": subscription.status,
                "is_active": active,
                "days_left": days_left,
                "expires_at": (
                    subscription.expires_at.isoformat()
                    if subscription.expires_at
                    else None
                ),
            }
        )

    return web.json_response(
        {
            "ok": True,
            "user": {
                "telegram_id": telegram_id,
                "first_name": auth["user"].get("first_name"),
                "username": auth["user"].get("username"),
            },
            "profile": {
                "active_count": active_count,
                "total_count": len(subscriptions),
                "max_days_left": max_days_left,
            },
            "subscriptions": subscription_items,
        }
    )


async def webapp_tariffs(request: web.Request):
    try:
        await get_webapp_user(request)
    except WebAppAuthError as error:
        return web.json_response(
            {"ok": False, "error": str(error)},
            status=401,
        )

    tariffs = []

    for code, tariff in TARIFFS.items():
        tariffs.append(
            {
                "code": code,
                "title": tariff["title"],
                "days": tariff["days"],
                "amount": tariff["amount"],
            }
        )

    return web.json_response(
        {
            "ok": True,
            "tariffs": tariffs,
        }
    )

async def webapp_create_order(request: web.Request):
    try:
        auth = await get_webapp_user(request)
    except WebAppAuthError as error:
        return web.json_response(
            {"ok": False, "error": str(error)},
            status=401,
        )

    telegram_id = auth["telegram_id"]

    try:
        payload = await request.json()
    except Exception:
        return web.json_response(
            {"ok": False, "error": "invalid_json"},
            status=400,
        )

    tariff_code = payload.get("tariff_code")
    action = payload.get("action", "buy")
    cer_id = payload.get("cer_id")
    customer_email = str(payload.get("email", "")).strip().lower()

    if tariff_code not in TARIFFS:
        return web.json_response(
            {"ok": False, "error": "unknown_tariff"},
            status=400,
        )

    if action not in ("buy", "renew"):
        return web.json_response(
            {"ok": False, "error": "unknown_action"},
            status=400,
        )

    if not is_valid_email(customer_email):
        return web.json_response(
            {
                "ok": False,
                "error": "invalid_email",
                "message": "Введите корректный email для отправки чека.",
            },
            status=400,
        )

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            return web.json_response(
                {
                    "ok": False,
                    "error": "user_not_found",
                    "message": "Сначала нажмите /start в боте.",
                },
                status=404,
            )

        if action == "buy":
            subscriptions = await get_user_subscriptions(
                session=session,
                telegram_id=telegram_id,
            )

            if len(visible_subscriptions(subscriptions)) >= 5:
                return web.json_response(
                    {
                        "ok": False,
                        "error": "subscriptions_limit",
                        "message": "У вас уже максимальное количество подписок: 5.",
                    },
                    status=400,
                )

            try:
                subscription = await create_new_pending_subscription(
                    session=session,
                    user_id=user.id,
                    telegram_id=telegram_id,
                )
            except ValueError:
                return web.json_response(
                    {
                        "ok": False,
                        "error": "subscriptions_limit",
                        "message": "У вас уже есть 5 созданных подписок.",
                    },
                    status=400,
                )

            order = await create_order(
                session=session,
                telegram_id=telegram_id,
                tariff_code=tariff_code,
                action="buy",
                subscription_id=subscription.id,
                cer_id=subscription.cer_id,
                customer_email=customer_email,
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
                return web.json_response(
                    {
                        "ok": False,
                        "error": "certificate_create_failed",
                        "message": "Не удалось подготовить данные для подключения.",
                        "details": str(error),
                    },
                    status=500,
                )

        else:
            subscription = await get_subscription_by_cer_id(
                session=session,
                cer_id=cer_id,
            )

            if (
                not subscription
                or subscription.telegram_id != telegram_id
                or subscription.status not in VISIBLE_SUBSCRIPTION_STATUSES
            ):
                return web.json_response(
                    {
                        "ok": False,
                        "error": "subscription_not_found",
                        "message": "Подписка для продления не найдена.",
                    },
                    status=404,
                )

            order = await create_order(
                session=session,
                telegram_id=telegram_id,
                tariff_code=tariff_code,
                action="renew",
                subscription_id=subscription.id,
                cer_id=subscription.cer_id,
                customer_email=customer_email,
            )

        try:
            payment_data = await init_tbank_payment(order)
        except Exception as error:
            return web.json_response(
                {
                    "ok": False,
                    "error": "payment_init_failed",
                    "message": "Не удалось создать ссылку на оплату.",
                    "details": str(error),
                },
                status=500,
            )

        payment_url = payment_data.get("PaymentURL")

        if not payment_url:
            return web.json_response(
                {
                    "ok": False,
                    "error": "payment_url_missing",
                    "message": "Банк не вернул ссылку на оплату.",
                },
                status=500,
            )

        order = await attach_payment_to_order(
            session=session,
            order_id=order.id,
            payment_id=str(payment_data.get("PaymentId")),
            payment_url=payment_url,
            payment_status=payment_data.get("Status"),
        )

    return web.json_response(
        {
            "ok": True,
            "order": {
                "id": order.id,
                "public_order_id": order.public_order_id,
                "amount": order.amount,
                "days": order.days,
                "tariff_code": order.tariff_code,
                "customer_email": order.customer_email,
            },
            "payment_url": order.payment_url,
        }
    )

def create_app():
    app = web.Application()

    app.router.add_post("/payments/tbank/webhook", tbank_webhook)
    app.router.add_get("/payments/success", payment_success)
    app.router.add_get("/payments/fail", payment_fail)

    app.router.add_get("/webapp/api/profile", webapp_profile)
    app.router.add_get("/webapp/api/tariffs", webapp_tariffs)
    app.router.add_post("/webapp/api/orders/create", webapp_create_order)

    return app


if __name__ == "__main__":
    web.run_app(
        create_app(),
        host="0.0.0.0",
        port=8080,
    )