from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from pathlib import Path
from app.database.session import AsyncSessionLocal
from app.services.strongswan_profile_service import create_strongswan_profile
from app.services.subscription_service import get_subscription_by_cer_id

router = Router()

ANDROID_APK_PATH = "/storage/apk/strongswan.apk"
IOS_CA_CERT_PATH = "storage/certs/cert_export_ca.zvotg.ru.crt"

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

def ios_setup_keyboard(cer_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📄 Скачать CA-сертификат",
                    callback_data="ios:download_ca",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔐 Скачать .p12 сертификат",
                    callback_data=f"download_cert:{cer_id}",
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

@router.callback_query(F.data.startswith("ios_setup:"))
async def ios_setup(callback: CallbackQuery):
    cer_id = callback.data.split(":", 1)[1]

    await safe_edit(
        callback,
        "🍎 *Apple iOS — установка IKEv2 VPN*\n\n"
        "*Шаг 1. Установите CA-сертификат*\n"
        "1. Нажмите кнопку *«Скачать CA-сертификат»* ниже.\n"
        "2. Откройте файл на iPhone.\n"
        "3. Разрешите установку профиля.\n"
        "4. Перейдите: *Настройки → Основные → VPN и управление устройством*.\n"
        "5. Выберите загруженный профиль и нажмите *Установить*.\n"
        "6. Затем перейдите: *Настройки → Основные → Об этом устройстве → Доверие сертификатов*.\n"
        "7. Включите полное доверие для установленного CA-сертификата.\n\n"
        "*Шаг 2. Установите клиентский сертификат*\n"
        "1. Нажмите *«Скачать .p12 сертификат»* ниже.\n"
        "2. Откройте `.p12` файл на iPhone.\n"
        "3. Установите профиль.\n"
        "4. Введите пароль: `123456789`.\n\n"
        "*Шаг 3. Добавьте VPN*\n"
        "1. Перейдите: *Настройки → VPN → Добавить конфигурацию VPN*.\n"
        "2. Тип: *IKEv2*.\n"
        "3. Сервер: *zvotg.ru*.\n"
        "4. Удалённый ID: *zvotg.ru*.\n"
        "5. Аутентификация пользователя: *Сертификат*.\n"
        "6. Выберите установленный клиентский сертификат.\n"
        "7. Сохраните и включите VPN.",
        reply_markup=ios_setup_keyboard(cer_id),
    )
    await callback.answer()

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

@router.callback_query(F.data == "ios:download_ca")
async def download_ios_ca(callback: CallbackQuery):
    ca_file = Path(IOS_CA_CERT_PATH)

    if not ca_file.exists():
        await callback.answer(
            f"CA-сертификат не найден: {IOS_CA_CERT_PATH}",
            show_alert=True,
        )
        return

    await callback.message.answer_document(
        document=FSInputFile(str(ca_file)),
        caption="📄 CA-сертификат для Apple iOS",
    )

    await callback.answer("CA-сертификат отправлен.")

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
