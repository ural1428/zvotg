import asyncio
import html
import json
import os
import re
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from dotenv import load_dotenv


load_dotenv()

SUPPORT_BOT_TOKEN = os.getenv("SUPPORT_BOT_TOKEN")
SUPPORT_ADMIN_CHAT_ID = int(os.getenv("SUPPORT_ADMIN_CHAT_ID", "0"))

if not SUPPORT_BOT_TOKEN:
    raise RuntimeError("SUPPORT_BOT_TOKEN не найден в .env")

if not SUPPORT_ADMIN_CHAT_ID:
    raise RuntimeError("SUPPORT_ADMIN_CHAT_ID не найден в .env")


bot = Bot(token=SUPPORT_BOT_TOKEN)
dp = Dispatcher()


STORAGE_DIR = Path("storage/support")
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

MESSAGE_MAP_FILE = STORAGE_DIR / "message_map.json"


def load_message_map() -> dict[str, int]:
    if not MESSAGE_MAP_FILE.exists():
        return {}

    try:
        return json.loads(MESSAGE_MAP_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_message_map(data: dict[str, int]) -> None:
    MESSAGE_MAP_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def remember_admin_message(admin_message_id: int, user_id: int) -> None:
    data = load_message_map()
    data[str(admin_message_id)] = user_id
    save_message_map(data)


def get_user_id_by_admin_message(admin_message_id: int) -> int | None:
    data = load_message_map()
    user_id = data.get(str(admin_message_id))

    if user_id is None:
        return None

    return int(user_id)


def extract_user_id_from_text(text: str | None) -> int | None:
    if not text:
        return None

    match = re.search(r"USER_ID:\s*(\d+)", text)

    if not match:
        return None

    return int(match.group(1))


def build_admin_header(message: Message) -> str:
    user = message.from_user

    username = f"@{user.username}" if user and user.username else "—"
    full_name = user.full_name if user else "—"
    user_id = user.id if user else 0

    text = message.text or message.caption or ""

    header = (
        "🆘 <b>Новое обращение</b>\n\n"
        f"USER_ID: <code>{user_id}</code>\n"
        f"Имя: <b>{html.escape(full_name)}</b>\n"
        f"Username: {html.escape(username)}\n\n"
        "Чтобы ответить пользователю, нажмите <b>Ответить</b> "
        "на это сообщение или на сообщение ниже."
    )

    if text:
        header += f"\n\n<b>Сообщение:</b>\n{html.escape(text)}"

    return header


@dp.message(CommandStart(), F.chat.type == "private")
async def start_handler(message: Message):
    await message.answer(
        "Здравствуйте 👋\n\n"
        "Это бот поддержки.\n"
        "Напишите ваш вопрос одним сообщением, и администратор ответит вам здесь."
    )


@dp.message(F.chat.type == "private")
async def user_message_handler(message: Message):
    user_id = message.from_user.id

    header_message = await bot.send_message(
        chat_id=SUPPORT_ADMIN_CHAT_ID,
        text=build_admin_header(message),
        parse_mode="HTML",
    )

    remember_admin_message(
        admin_message_id=header_message.message_id,
        user_id=user_id,
    )

    # Копируем исходное сообщение пользователя в админ-группу.
    # Так админ увидит фото, файл, видео, голосовое и т.д.
    try:
        copied_message = await bot.copy_message(
            chat_id=SUPPORT_ADMIN_CHAT_ID,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
        )

        remember_admin_message(
            admin_message_id=copied_message.message_id,
            user_id=user_id,
        )
    except Exception:
        # Если Telegram не смог скопировать тип сообщения,
        # заголовок всё равно уже отправлен.
        pass

    await message.answer(
        "✅ Ваше сообщение отправлено в поддержку.\n"
        "Ответ придёт сюда, в этот чат."
    )


@dp.message(F.chat.id == SUPPORT_ADMIN_CHAT_ID)
async def admin_reply_handler(message: Message):
    if not message.reply_to_message:
        return

    replied_message_id = message.reply_to_message.message_id

    user_id = get_user_id_by_admin_message(replied_message_id)

    if user_id is None:
        user_id = extract_user_id_from_text(message.reply_to_message.text)

    if user_id is None:
        await message.reply(
            "Не удалось определить пользователя.\n"
            "Ответьте на сообщение, где есть USER_ID."
        )
        return

    try:
        await bot.send_message(
            chat_id=user_id,
            text="💬 <b>Поддержка:</b>",
            parse_mode="HTML",
        )

        await bot.copy_message(
            chat_id=user_id,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
        )

        await message.reply("✅ Ответ отправлен пользователю.")
    except Exception as error:
        await message.reply(
            "❌ Не удалось отправить ответ пользователю.\n\n"
            f"Ошибка: <code>{html.escape(str(error))}</code>",
            parse_mode="HTML",
        )


async def main():
    print("Support bot started")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
