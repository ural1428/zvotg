from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from app.database.session import AsyncSessionLocal
from app.services.strongswan_profile_service import create_strongswan_profile
from app.services.subscription_service import get_subscription_by_cer_id

router = Router()

ANDROID_APK_PATH = "/storage/apk/strongswan.apk"


def android_setup_keyboard(cer_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
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
                    callback_data=f"android:download_profile:{cer_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅ Назад",
                    callback_data="menu:support",
                )
            ],
        ]
    )


async def safe_edit(callback: CallbackQuery, text: str, reply_markup=None):
    try:
        await callback.message.edit_text(
            text,
            reply_markup=reply_markup,
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )
    except TelegramBadRequest:
        await callback.message.answer(
            text,
            reply_markup=reply_markup,
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )


@router.callback_query(F.data.startswith("android_setup:"))
async def android_setup(callback: CallbackQuery):
    cer_id = callback.data.split(":", 1)[1]

    await safe_edit(
        callback,
        "🤖 *Быстрая установка VPN на Android*\n\n"
        "1. Скачайте [StrongSwan из Google Play]"
        "(https://play.google.com/store/apps/details?id=org.strongswan.android) "
        "или скачайте APK файл по кнопке ниже.\n\n"
        "2. Нажмите *«Загрузить профиль»*.\n\n"
        "3. Введите пароль: `123456789`.\n\n"
        "4. Два раза нажмите *OK*.\n\n"
        "5. Выберите *«Выбрать»*. Чек-бокс уже будет стоять на вашем сертификате.\n\n"
        "6. Нажмите *IMPORT* в правом верхнем углу.",
        reply_markup=android_setup_keyboard(cer_id),
    )

    await callback.answer()


@router.callback_query(F.data == "android:download_apk")
async def download_strongswan_apk(callback: CallbackQuery):
    try:
        await callback.message.answer_document(
            document=FSInputFile(ANDROID_APK_PATH),
            caption="📦 APK StrongSwan для Android",
        )
        await callback.answer("APK отправлен.")
    except FileNotFoundError:
        await callback.answer(
            "APK файл пока не загружен на сервер.",
            show_alert=True,
        )


@router.callback_query(F.data.startswith("android:download_profile:"))
async def download_android_profile(callback: CallbackQuery):
    cer_id = callback.data.split(":")[-1]

    async with AsyncSessionLocal() as session:
        subscription = await get_subscription_by_cer_id(
            session=session,
            cer_id=cer_id,
        )

        if not subscription or subscription.telegram_id != callback.from_user.id:
            await callback.answer(
                "Подписка не найдена.",
                show_alert=True,
            )
            return

        try:
            sswan_path = create_strongswan_profile(
                cer_id=subscription.cer_id,
                p12_path=subscription.cert_path,
            )
        except FileNotFoundError:
            await callback.answer(
                "Файл сертификата не найден.",
                show_alert=True,
            )
            return

    await callback.message.answer_document(
        document=FSInputFile(sswan_path),
        caption=(
            "⚡ Профиль StrongSwan\n\n"
            "Откройте этот файл на Android и импортируйте профиль."
        ),
    )

    await callback.answer("Профиль отправлен.")
