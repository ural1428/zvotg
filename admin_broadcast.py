import argparse
import asyncio
from pathlib import Path

from aiogram import Bot
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramRetryAfter,
)
from aiogram.types import FSInputFile
from sqlalchemy import select

from app.config import config
from app.database.models import User
from app.database.session import AsyncSessionLocal


SEND_DELAY_SECONDS = 0.08


async def get_users():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User.telegram_id).order_by(User.id)
        )

        return [row[0] for row in result.all()]


async def safe_send(
    bot: Bot,
    telegram_id: int,
    text: str | None = None,
    photo_path: str | None = None,
    video_path: str | None = None,
    document_path: str | None = None,
):
    try:
        if photo_path:
            await bot.send_photo(
                chat_id=telegram_id,
                photo=FSInputFile(photo_path),
                caption=text,
                parse_mode="HTML",
            )

        elif video_path:
            await bot.send_video(
                chat_id=telegram_id,
                video=FSInputFile(video_path),
                caption=text,
                parse_mode="HTML",
            )

        elif document_path:
            await bot.send_document(
                chat_id=telegram_id,
                document=FSInputFile(document_path),
                caption=text,
                parse_mode="HTML",
            )

        else:
            await bot.send_message(
                chat_id=telegram_id,
                text=text or "",
                parse_mode="HTML",
            )

        return True, None

    except TelegramRetryAfter as error:
        await asyncio.sleep(error.retry_after + 1)
        return await safe_send(
            bot=bot,
            telegram_id=telegram_id,
            text=text,
            photo_path=photo_path,
            video_path=video_path,
            document_path=document_path,
        )

    except TelegramForbiddenError:
        return False, "bot_blocked_or_chat_not_found"

    except TelegramBadRequest as error:
        return False, str(error)

    except Exception as error:
        return False, str(error)


async def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--text",
        required=True,
        help="Текст рассылки. Можно использовать HTML: <b>жирный</b>",
    )

    parser.add_argument(
        "--photo",
        default=None,
        help="Путь к картинке",
    )

    parser.add_argument(
        "--video",
        default=None,
        help="Путь к видео",
    )

    parser.add_argument(
        "--document",
        default=None,
        help="Путь к файлу",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Только показать количество пользователей, ничего не отправлять",
    )

    args = parser.parse_args()

    media_paths = [args.photo, args.video, args.document]
    media_count = len([path for path in media_paths if path])

    if media_count > 1:
        raise RuntimeError("Можно указать только один тип файла: photo, video или document")

    for path in media_paths:
        if path and not Path(path).exists():
            raise FileNotFoundError(f"Файл не найден: {path}")

    users = await get_users()

    print(f"Найдено пользователей: {len(users)}")

    if args.dry_run:
        print("DRY RUN: рассылка не отправлена")
        return

    bot = Bot(token=config.bot_token)

    success = 0
    failed = 0

    try:
        for index, telegram_id in enumerate(users, start=1):
            ok, error = await safe_send(
                bot=bot,
                telegram_id=telegram_id,
                text=args.text,
                photo_path=args.photo,
                video_path=args.video,
                document_path=args.document,
            )

            if ok:
                success += 1
                print(f"[{index}/{len(users)}] OK {telegram_id}")
            else:
                failed += 1
                print(f"[{index}/{len(users)}] FAIL {telegram_id}: {error}")

            await asyncio.sleep(SEND_DELAY_SECONDS)

    finally:
        await bot.session.close()

    print()
    print("Рассылка завершена")
    print(f"Успешно: {success}")
    print(f"Ошибок: {failed}")


if __name__ == "__main__":
    asyncio.run(main())
