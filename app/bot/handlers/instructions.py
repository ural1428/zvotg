from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup

router = Router()

ANDROID_APK_PATH = "/storage/apk/strongswan.apk"
IOS_CA_CERT_PATH = "/storage/cert/ca.crt"


android_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📲 Скачать strongSwan в Google Play",
                url="https://play.google.com/store/apps/details?id=org.strongswan.android",
            )
        ],
        [
            InlineKeyboardButton(
                text="📦 Скачать APK с сервера",
                callback_data="instruction:android:apk",
            )
        ],
    ]
)


@router.callback_query(F.data == "instruction:android")
async def instruction_android(callback: CallbackQuery):
    await callback.message.answer(
        "🤖 Android — установка IKEv2 VPN\n\n"
        "1. Скачайте приложение strongSwan VPN Client.\n"
        "2. Откройте strongSwan.\n"
        "3. Нажмите «Добавить VPN-профиль».\n"
        "4. В поле Server укажите адрес вашего VPN-сервера.\n"
        "5. В типе подключения выберите IKEv2 Certificate / сертификат.\n"
        "6. Импортируйте полученный `.p12` сертификат.\n"
        "7. Введите пароль сертификата: `1234567890`.\n"
        "8. Сохраните профиль и нажмите «Подключиться».\n\n"
        "Если Google Play недоступен, скачайте APK с сервера.",
        reply_markup=android_keyboard,
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "instruction:android:apk")
async def download_android_apk(callback: CallbackQuery):
    try:
        await callback.message.answer_document(
            document=FSInputFile(ANDROID_APK_PATH),
            caption="📦 strongSwan APK для Android",
        )
        await callback.answer("APK отправлен.")
    except FileNotFoundError:
        await callback.answer("APK файл пока не загружен на сервер.", show_alert=True)


@router.callback_query(F.data == "instruction:ios")
async def instruction_ios(callback: CallbackQuery):
    await callback.message.answer_document(
        document=FSInputFile(IOS_CA_CERT_PATH),
        caption=(
            "🍎 Apple iOS — настройка IKEv2 VPN\n\n"
            "Сначала установите CA-сертификат из этого сообщения.\n\n"
            "1. Нажмите на CA-сертификат и разрешите установку профиля.\n"
            "2. Откройте: Настройки → Основные → VPN и управление устройством.\n"
            "3. Установите загруженный профиль CA.\n"
            "4. Затем откройте: Настройки → Основные → Об этом устройстве → Доверие сертификатов.\n"
            "5. Включите полное доверие для установленного CA-сертификата.\n"
            "6. После этого установите ваш `.p12` сертификат из сообщения с сертификатом.\n"
            "7. Введите пароль сертификата: `1234567890`.\n"
            "8. Перейдите: Настройки → VPN → Добавить конфигурацию VPN.\n"
            "9. Тип: IKEv2.\n"
            "10. Сервер и удалённый ID: адрес вашего VPN-сервера.\n"
            "11. Локальный ID можно оставить пустым, если не требуется.\n"
            "12. Аутентификация пользователя: Сертификат.\n"
            "13. Выберите установленный клиентский сертификат.\n"
            "14. Сохраните и включите VPN."
        ),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "instruction:windows")
async def instruction_windows(callback: CallbackQuery):
    await callback.message.answer(
        "🪟 Windows — настройка IKEv2 VPN\n\n"
        "1. Скачайте `.p12` сертификат из сообщения бота.\n"
        "2. Дважды нажмите на файл сертификата.\n"
        "3. Выберите «Текущий пользователь».\n"
        "4. Введите пароль сертификата: `1234567890`.\n"
        "5. Хранилище сертификатов можно оставить автоматическим.\n"
        "6. Откройте: Параметры → Сеть и Интернет → VPN.\n"
        "7. Нажмите «Добавить VPN».\n"
        "8. Поставщик VPN: Windows встроенный.\n"
        "9. Имя подключения: любое, например VPN.\n"
        "10. Имя или адрес сервера: адрес вашего VPN-сервера.\n"
        "11. Тип VPN: IKEv2.\n"
        "12. Тип данных для входа: Сертификат.\n"
        "13. Сохраните подключение и нажмите «Подключиться»."
    )
    await callback.answer()


@router.callback_query(F.data == "instruction:macos")
async def instruction_macos(callback: CallbackQuery):
    await callback.message.answer(
        "💻 Apple macOS — настройка IKEv2 VPN\n\n"
        "1. Скачайте `.p12` сертификат из сообщения бота.\n"
        "2. Дважды нажмите на сертификат — он откроется в Связке ключей.\n"
        "3. Введите пароль сертификата: `1234567890`.\n"
        "4. Убедитесь, что сертификат добавлен в «Вход» / Login.\n"
        "5. Откройте: Системные настройки → VPN.\n"
        "6. Добавьте новую конфигурацию VPN.\n"
        "7. Тип VPN: IKEv2.\n"
        "8. Server Address: адрес вашего VPN-сервера.\n"
        "9. Remote ID: адрес вашего VPN-сервера.\n"
        "10. Local ID можно оставить пустым, если не требуется.\n"
        "11. Authentication Settings → Certificate.\n"
        "12. Выберите установленный сертификат.\n"
        "13. Сохраните и подключитесь."
    )
    await callback.answer()
