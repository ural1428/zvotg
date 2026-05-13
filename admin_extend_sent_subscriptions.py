import argparse
import asyncio
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest, TelegramRetryAfter
from sqlalchemy import select

from app.config import config
from app.database.models import VPNSubscription
from app.database.session import AsyncSessionLocal


BONUS_DAYS = 60
TARGET_STATUS = "sent"

DEFAULT_MESSAGE = (
    "🎁 Вам начислен бонус!\n"
    "Мы снизили стоимость тарифов! И в связи с этим добавили к вашей активной подписке +60 дней.\n\n"
    "Спасибо, что пользуетесь нашим VPN-сервисом.\n"
    "Расскажите о нас своим знакомым и друзьям!"
)


def normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def add_days_to_subscription(subscription: VPNSubscription, days: int) -> None:
    now = datetime.now(timezone.utc)

    expires_at = normalize_datetime(subscription.expires_at)

    if expires_at and expires_at > now:
        base_date = expires_at
    else:
        base_date = now

    subscription.expires_at = base_date + timedelta(days=days)


async def send_message_safe(bot: Bot, telegram_id: int, text: str) -> tuple[bool, str | None]:
    try:
        await bot.send_message(
            chat_id=telegram_id,
            text=text,
        )
        return True, None

    except TelegramRetryAfter as error:
        await asyncio.sleep(error.retry_after + 1)
        return await send_message_safe(bot, telegram_id, text)

    except TelegramForbiddenError:
        return False, "Пользователь заблокировал бота или чат недоступен"

    except TelegramBadRequest as error:
        return False, str(error)

    except Exception as error:
        return False, str(error)


async def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--yes",
        action="store_true",
        help="Подтвердить выполнение без ручного ввода YES",
    )
    
    parser.add_argument(
        "--days",
        type=int,
        default=BONUS_DAYS,
        help="Сколько дней добавить",
    )

    parser.add_argument(
        "--message",
        default=DEFAULT_MESSAGE,
        help="Сообщение пользователям",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Только показать, кому будет начислено, без изменений и рассылки",
    )

    args = parser.parse_args()

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(VPNSubscription)
            .where(VPNSubscription.status == TARGET_STATUS)
            .order_by(VPNSubscription.id)
        )

        subscriptions = list(result.scalars().all())

        if not subscriptions:
            print(f"Подписок со статусом '{TARGET_STATUS}' не найдено.")
            return

        telegram_ids = sorted({subscription.telegram_id for subscription in subscriptions})

        print(f"Найдено подписок со статусом '{TARGET_STATUS}': {len(subscriptions)}")
        print(f"Уникальных пользователей: {len(telegram_ids)}")
        print()

        for subscription in subscriptions:
            print(
                f"id={subscription.id} "
                f"telegram_id={subscription.telegram_id} "
                f"cer_id={subscription.cer_id} "
                f"expires_at={subscription.expires_at}"
            )

        if args.dry_run:
            print()
            print("DRY RUN: изменения не внесены, сообщения не отправлены.")
            return

        if not args.yes:
            print()
            print(f"Будет добавлено +{args.days} дней подпискам со статусом '{TARGET_STATUS}'.")
            print(f"Сообщение будет отправлено пользователям: {len(telegram_ids)}")
            print()
            print("Для реального запуска добавь флаг --yes")
            print("Пример:")
            print(f"python admin_extend_sent_subscriptions.py --days {args.days} --yes")
            return

        for subscription in subscriptions:
            add_days_to_subscription(subscription, args.days)

        await session.commit()

        print()
        print(f"Готово: +{args.days} дней добавлено к {len(subscriptions)} подпискам.")
        print("Начинаю рассылку...")

    bot = Bot(token=config.bot_token)

    success = 0
    failed = 0

    try:
        for index, telegram_id in enumerate(telegram_ids, start=1):
            ok, error = await send_message_safe(
                bot=bot,
                telegram_id=telegram_id,
                text=args.message,
            )

            if ok:
                success += 1
                print(f"[{index}/{len(telegram_ids)}] OK {telegram_id}")
            else:
                failed += 1
                print(f"[{index}/{len(telegram_ids)}] FAIL {telegram_id}: {error}")

            await asyncio.sleep(0.08)

    finally:
        await bot.session.close()

    print()
    print("Рассылка завершена.")
    print(f"Успешно отправлено: {success}")
    print(f"Ошибок: {failed}")


if __name__ == "__main__":
    asyncio.run(main())
