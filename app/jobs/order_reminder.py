import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select

from app.config import config
from app.database.models import Order
from app.database.session import AsyncSessionLocal
from app.services.tariffs import TARIFFS


MSK = ZoneInfo("Europe/Moscow")


def payment_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💳 Оплатить",
                    callback_data=f"order:pay:{order_id}",
                )
            ]
        ]
    )


async def send_order_reminders():
    now = datetime.now(MSK)
    bot = Bot(token=config.bot_token)

    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Order).where(
                    Order.status.in_(["created", "pending_payment"]),
                    Order.reminders_sent < 2,
                )
            )

            orders = result.scalars().all()

            for order in orders:
                created_at = order.created_at.astimezone(MSK)

                should_send = False

                if order.reminders_sent == 0:
                    should_send = created_at <= now - timedelta(hours=1)

                elif order.reminders_sent == 1 and order.last_reminder_at:
                    last_reminder_at = order.last_reminder_at.astimezone(MSK)
                    should_send = last_reminder_at <= now - timedelta(hours=3)

                if not should_send:
                    continue

                tariff = TARIFFS.get(order.tariff_code, {})
                tariff_title = tariff.get("title", order.tariff_code)

                await bot.send_message(
                    chat_id=order.telegram_id,
                    text=(
                        "⏳ У вас есть незавершённый заказ\n\n"
                        f"🧾 Заказ: #{order.id}\n"
                        f"📋 Тариф: {tariff_title}\n"
                        f"💰 Сумма: {order.amount} ₽\n\n"
                        "Вы можете оплатить его сейчас."
                    ),
                    reply_markup=payment_keyboard(order.id),
                )

                order.reminders_sent += 1
                order.last_reminder_at = now

            await session.commit()

    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(send_order_reminders())
