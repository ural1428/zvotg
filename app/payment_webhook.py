from aiohttp import web
from aiogram import Bot

from app.config import config
from app.database.session import AsyncSessionLocal
from app.services.order_service import get_order_by_id, mark_order_paid
from app.services.referral_service import reward_referrer_for_paid_user
from app.services.subscription_service import (
    activate_or_extend_subscription,
    get_subscription_by_cer_id,
    send_certificate,
)
from app.services.tbank_service import verify_tbank_notification


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


def create_app():
    app = web.Application()

    app.router.add_post("/payments/tbank/webhook", tbank_webhook)
    app.router.add_get("/payments/success", payment_success)
    app.router.add_get("/payments/fail", payment_fail)

    return app


if __name__ == "__main__":
    web.run_app(
        create_app(),
        host="0.0.0.0",
        port=8080,
    )