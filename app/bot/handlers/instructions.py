from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest

router = Router()

ANDROID_APK_PATH = "/storage/apk/strongswan.apk"
IOS_CA_CERT_PATH = "/storage/cert/ca.crt"


def instruction_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅ Назад",
                    callback_data="menu:support",
                )
            ]
        ]
    )


def android_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📲 strongSwan в Google Play",
                    url="https://play.google.com/store/apps/details?id=org.strongswan.android",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📦 Скачать APK",
                    callback_data="instruction:android:apk",
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


def ios_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📄 Скачать CA-сертификат",
                    callback_data="instruction:ios:ca",
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
        )
    except TelegramBadRequest:
        await callback.message.answer(
            text,
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )


@router.callback_query(F.data == "instruction:android")
async def instruction_android(callback: CallbackQuery):
    await safe_edit(
        callback,
        "🤖 *Android — установка IKEv2 VPN*\n\n"
        "1. Скачайте приложение *strongSwan VPN Client*.\n"
        "2. Откройте strongSwan.\n"
        "3. Нажмите *Add VPN Profile* / *Добавить VPN-профиль*.\n"
        "4. В поле *Server* укажите адрес VPN-сервера.\n"
        "5. Тип подключения выберите *IKEv2 Certificate*.\n"
        "6. Импортируйте полученный `.p12` сертификат.\n"
        "7. Введите пароль сертификата: `1234567890`.\n"
        "8. Сохраните профиль.\n"
        "9. Нажмите на созданный профиль для подключения.\n\n"
        "Если Google Play недоступен — скачайте APK с сервера.",
        reply_markup=android_keyboard(),
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
        await callback.answer(
            "APK файл пока не загружен на сервер.",
            show_alert=True,
        )


@router.callback_query(F.data == "instruction:ios")
async def instruction_ios(callback: CallbackQuery):
    await safe_edit(
        callback,
        "🍎 *Apple iOS — установка IKEv2 VPN*\n\n"
        "*Важно:* для iOS нужно установить два сертификата:\n"
        "1. CA-сертификат\n"
        "2. Ваш клиентский `.p12` сертификат\n\n"
        "*Шаг 1. Установите CA-сертификат*\n"
        "1. Нажмите кнопку *Скачать CA-сертификат* ниже.\n"
        "2. Откройте скачанный файл на iPhone.\n"
        "3. Разрешите установку профиля.\n"
        "4. Перейдите: *Настройки → Основные → VPN и управление устройством*.\n"
        "5. Установите загруженный профиль.\n"
        "6. Затем перейдите: *Настройки → Основные → Об этом устройстве → Доверие сертификатов*.\n"
        "7. Включите полное доверие для установленного CA-сертификата.\n\n"
        "*Шаг 2. Установите клиентский сертификат*\n"
        "1. Откройте `.p12` файл, который прислал бот.\n"
        "2. Установите профиль.\n"
        "3. Введите пароль сертификата: `1234567890`.\n\n"
        "*Шаг 3. Создайте VPN-подключение*\n"
        "1. Перейдите: *Настройки → VPN → Добавить конфигурацию VPN*.\n"
        "2. Тип: *IKEv2*.\n"
        "3. В поле *Сервер* укажите адрес VPN-сервера.\n"
        "4. В поле *Удалённый ID* укажите адрес VPN-сервера.\n"
        "5. Аутентификация пользователя: *Сертификат*.\n"
        "6. Выберите установленный клиентский сертификат.\n"
        "7. Сохраните и включите VPN.",
        reply_markup=ios_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "instruction:ios:ca")
async def download_ios_ca(callback: CallbackQuery):
    try:
        await callback.message.answer_document(
            document=FSInputFile(IOS_CA_CERT_PATH),
            caption="📄 CA-сертификат для Apple iOS",
        )
        await callback.answer("CA-сертификат отправлен.")
    except FileNotFoundError:
        await callback.answer(
            "CA-сертификат пока не загружен на сервер.",
            show_alert=True,
        )


@router.callback_query(F.data == "instruction:windows")
async def instruction_windows(callback: CallbackQuery):
    await safe_edit(
        callback,
        "🪟 *Windows — установка IKEv2 VPN*\n\n"
        "1. Скачайте `.p12` сертификат из сообщения бота.\n"
        "2. Дважды нажмите на файл сертификата.\n"
        "3. Выберите *Текущий пользователь*.\n"
        "4. Введите пароль сертификата: `1234567890`.\n"
        "5. Хранилище сертификатов можно оставить автоматическим.\n"
        "6. Откройте: *Параметры → Сеть и Интернет → VPN*.\n"
        "7. Нажмите *Добавить VPN*.\n"
        "8. Поставщик VPN: *Windows встроенный*.\n"
        "9. Имя подключения: любое, например `VPN`.\n"
        "10. Имя или адрес сервера: адрес VPN-сервера.\n"
        "11. Тип VPN: *IKEv2*.\n"
        "12. Тип данных для входа: *Сертификат*.\n"
        "13. Сохраните подключение и нажмите *Подключиться*.",
        reply_markup=instruction_back_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "instruction:macos")
async def instruction_macos(callback: CallbackQuery):
    await safe_edit(
        callback,
        "💻 *Apple macOS — установка IKEv2 VPN*\n\n"
        "1. Скачайте `.p12` сертификат из сообщения бота.\n"
        "2. Дважды нажмите на сертификат — он откроется в *Связке ключей*.\n"
        "3. Введите пароль сертификата: `1234567890`.\n"
        "4. Убедитесь, что сертификат добавлен в раздел *Вход / Login*.\n"
        "5. Откройте: *Системные настройки → VPN*.\n"
        "6. Добавьте новую конфигурацию VPN.\n"
        "7. Тип VPN: *IKEv2*.\n"
        "8. *Server Address*: адрес VPN-сервера.\n"
        "9. *Remote ID*: адрес VPN-сервера.\n"
        "10. *Local ID* можно оставить пустым.\n"
        "11. Authentication Settings → *Certificate*.\n"
        "12. Выберите установленный сертификат.\n"
        "13. Сохраните и подключитесь.",
        reply_markup=instruction_back_keyboard(),
    )
    await callback.answer()
