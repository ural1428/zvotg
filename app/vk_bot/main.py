import re

import asyncio
import json
import os
import random
from typing import Any

import aiohttp
from dotenv import load_dotenv
from sqlalchemy import and_, or_, select
from pathlib import Path
from app.database.models import User, VPNSubscription
from app.database.session import AsyncSessionLocal
from app.services.account_link_service import (
    apply_link_code,
    approve_merge_request,
    cancel_merge_request,
    create_account_link_code,
    create_account_merge_request,
    get_or_create_platform_user,
    get_pending_merge_request,
    get_user_stats,
)
from app.services.subscription_service import (
    get_subscription_days_left,
    is_subscription_active,
)
from app.services.tariffs import TARIFFS

from app.config import config
from app.integrations.mikrotik.manager import MikroTikManager
from app.services.platform_order_service import create_platform_order
from app.services.strongswan_profile_service import create_strongswan_profile
from app.services.platform_subscription_service import (
    create_platform_pending_subscription,
    get_active_platform_subscriptions,
    mark_platform_cert_created,
)
from app.services.order_service import attach_payment_to_order
from app.services.tbank_service import init_tbank_payment
from app.services.strongswan_profile_service import create_strongswan_profile


load_dotenv()

VK_BOT_TOKEN = os.getenv("VK_BOT_TOKEN")
VK_GROUP_ID = os.getenv("VK_GROUP_ID")
VK_API_VERSION = os.getenv("VK_API_VERSION", "5.199")

if not VK_BOT_TOKEN:
    raise RuntimeError("VK_BOT_TOKEN не найден в .env")

if not VK_GROUP_ID:
    raise RuntimeError("VK_GROUP_ID не найден в .env")

PROJECT_ROOT = Path(__file__).resolve().parents[2]

VK_ANDROID_VIDEO_PATH = os.getenv("VK_ANDROID_VIDEO_PATH", "storage/video/strongswan_small.mp4")
VK_IOS_VIDEO_PATH = os.getenv("VK_IOS_VIDEO_PATH", "storage/video/ios_instruction.mp4")
VK_CA_CERT_PATH = os.getenv("VK_CA_CERT_PATH", "storage/certs/cert_export_ca.zvotg.ru.crt")


def resolve_project_path(path: str | Path | None) -> Path | None:
    if not path:
        return None

    file_path = Path(path)

    if file_path.is_absolute():
        return file_path

    return PROJECT_ROOT / file_path


VK_API_URL = "https://api.vk.com/method"

VISIBLE_SUBSCRIPTION_STATUSES = ("paid", "sent", "expired")

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


class VKBot:
    def __init__(self):
        self.session: aiohttp.ClientSession | None = None
        self.server: str | None = None
        self.key: str | None = None
        self.ts: str | None = None
        self.pending_payments: dict[int, dict[str, Any]] = {}

    async def start(self):
        self.session = aiohttp.ClientSession()

        await self.init_longpoll()

        print("VK bot started")

        while True:
            try:
                await self.poll()
            except asyncio.CancelledError:
                raise
            except Exception as error:
                print(f"VK bot error: {error}")
                await asyncio.sleep(3)

                try:
                    await self.init_longpoll()
                except Exception as init_error:
                    print(f"VK Long Poll reinit error: {init_error}")
                    await asyncio.sleep(5)

    async def close(self):
        if self.session:
            await self.session.close()

    async def api_call(
        self,
        method: str,
        params: dict[str, Any] | None = None,
    ):
        if not self.session:
            raise RuntimeError("Session is not initialized")

        payload = {
            "access_token": VK_BOT_TOKEN,
            "v": VK_API_VERSION,
        }

        if params:
            payload.update(params)

        async with self.session.post(
            f"{VK_API_URL}/{method}",
            data=payload,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            data = await response.json(content_type=None)

        if "error" in data:
            raise RuntimeError(f"VK API error: {data['error']}")

        return data["response"]

    async def init_longpoll(self):
        data = await self.api_call(
            "groups.getLongPollServer",
            {
                "group_id": VK_GROUP_ID,
            },
        )

        self.server = data["server"]
        self.key = data["key"]
        self.ts = data["ts"]

        print("VK Long Poll initialized")

    async def poll(self):
        if not self.session or not self.server or not self.key or not self.ts:
            await self.init_longpoll()

        params = {
            "act": "a_check",
            "key": self.key,
            "ts": self.ts,
            "wait": 25,
        }

        async with self.session.get(
            self.server,
            params=params,
            timeout=aiohttp.ClientTimeout(total=35),
        ) as response:
            data = await response.json(content_type=None)

        if "failed" in data:
            print(f"Long Poll failed: {data}")
            await self.init_longpoll()
            return

        self.ts = data["ts"]

        for update in data.get("updates", []):
            await self.handle_update(update)

    async def handle_update(self, update: dict[str, Any]):
        event_type = update.get("type")

        if event_type != "message_new":
            return

        message = update.get("object", {}).get("message", {})

        peer_id = message.get("peer_id")
        from_id = message.get("from_id")
        text = (message.get("text") or "").strip()

        payload_raw = message.get("payload")
        payload = None

        if payload_raw:
            try:
                payload = json.loads(payload_raw)
            except json.JSONDecodeError:
                payload = None

        if not peer_id:
            return

        # Работаем только с личными сообщениями.
        # В личке VK peer_id обычно равен from_id.
        if from_id and peer_id != from_id:
            return

        await self.handle_message(
            peer_id=peer_id,
            vk_user_id=from_id or peer_id,
            text=text,
            payload=payload,
        )

    async def get_or_create_vk_user(self, peer_id: int) -> User:
        async with AsyncSessionLocal() as session:
            user = await get_or_create_platform_user(
                session=session,
                platform="vk",
                external_id=peer_id,
            )

            return user

    async def get_user_subscriptions(self, user: User) -> list[VPNSubscription]:
        conditions = [
            VPNSubscription.user_id == user.id,
        ]

        if user.telegram_id is not None:
            conditions.append(
                VPNSubscription.telegram_id == user.telegram_id,
            )

        if user.vk_peer_id is not None:
            conditions.append(
                and_(
                    VPNSubscription.owner_platform == "vk",
                    VPNSubscription.owner_external_id == user.vk_peer_id,
                )
            )

        if user.primary_platform and user.primary_external_id:
            conditions.append(
                and_(
                    VPNSubscription.owner_platform == user.primary_platform,
                    VPNSubscription.owner_external_id == user.primary_external_id,
                )
            )

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(VPNSubscription)
                .where(or_(*conditions))
                .where(VPNSubscription.status.in_(VISIBLE_SUBSCRIPTION_STATUSES))
                .order_by(VPNSubscription.id)
            )

            return list(result.scalars().all())

    async def handle_message(
        self,
        peer_id: int,
        vk_user_id: int,
        text: str,
        payload: dict[str, Any] | None = None,
    ):
        normalized = text.lower().strip()

        # Создаём или находим VK-пользователя при любом взаимодействии.
        await self.get_or_create_vk_user(peer_id)

        if normalized in {"✅ да, объединить", "да, объединить", "да", "объединить",}:
            await self.confirm_merge(peer_id)
            return

        if normalized in {"❌ нет, оставить отдельно", "нет", "отмена", "не объединять",}:
            await self.cancel_merge(peer_id)
            return

        if normalized in {"/start", "start", "начать", "привет", "меню"}:
            await self.send_main_menu(peer_id)
            return

        if normalized in {"👤 профиль", "профиль"}:
            await self.show_profile(peer_id)
            return

        if normalized in {"💳 тарифы", "тарифы", "купить", "подписка"}:
            await self.show_tariffs(peer_id)
            return

        if normalized in {"🔗 привязка", "привязка", "привязать"}:
            await self.show_link_code(peer_id)
            return

        if normalized in {"💬 поддержка", "поддержка"}:
            await self.show_support(peer_id)
            return

        if normalized.isdigit() and len(normalized) == 6:
            await self.process_link_code(
                peer_id=peer_id,
                code=normalized,
            )
            return

        if payload:
            await self.handle_payload(
                peer_id=peer_id,
                payload=payload,
            )
            return

        if peer_id in self.pending_payments:
            await self.process_payment_email(
                peer_id=peer_id,
                email=text,
            )
            return

        await self.send_message(
            peer_id=peer_id,
            message="Выберите действие в меню ниже 👇",
            keyboard=main_keyboard(),
        )

    async def send_main_menu(self, peer_id: int):
        await self.send_message(
            peer_id=peer_id,
            message=(
                "👋 Добро пожаловать!\n\n"
                "Это VK-бот сервиса.\n"
                "Он будет работать с тем же аккаунтом, что и Telegram-бот, "
                "после привязки профилей.\n\n"
                "Выберите действие:"
            ),
            keyboard=main_keyboard(),
        )

    async def show_profile(self, peer_id: int):
        user = await self.get_or_create_vk_user(peer_id)
        subscriptions = await self.get_user_subscriptions(user)

        active_count = 0
        max_days_left = 0

        lines = [
            "👤 Профиль\n",
            f"VK peer_id: {user.vk_peer_id or 'не привязан'}",
            f"Telegram ID: {user.telegram_id or 'не привязан'}",
            "",
            f"Основная платформа: {user.primary_platform or 'не указана'}",
            f"Основной ID: {user.primary_external_id or 'не указан'}",
            "",
        ]

        if not subscriptions:
            lines.extend(
                [
                    "Подписок пока нет.",
                    "",
                    "Вы можете выбрать тариф и оформить подписку через VK-бота.",
                ]
            )

            await self.send_message(
                peer_id=peer_id,
                message="\n".join(lines),
                keyboard=profile_empty_keyboard(),
            )
            return

        lines.append("📦 Подписки:")

        for index, subscription in enumerate(subscriptions, start=1):
            is_active = is_subscription_active(subscription)
            days_left = get_subscription_days_left(subscription)

            if is_active:
                active_count += 1
                max_days_left = max(max_days_left, days_left)

            if subscription.status == "expired":
                status_text = "❌ Истекла"
            elif is_active:
                status_text = "✅ Активна"
            else:
                status_text = "⚠️ Не активна"

            lines.extend(
                [
                    "",
                    f"🔐 Подписка #{index}",
                    f"Статус: {status_text}",
                    f"ID сертификата: {subscription.cer_id}",
                    f"Осталось: {days_left} дн.",
                ]
            )

        lines.extend(
            [
                "",
                f"Активных подписок: {active_count}",
                f"Всего подписок: {len(subscriptions)}",
                f"Максимально осталось: {max_days_left} дн.",
            ]
        )

        await self.send_message(
            peer_id=peer_id,
            message="\n".join(lines),
            keyboard=profile_subscriptions_keyboard(subscriptions),
        )

    async def find_subscription_for_peer(
        self,
        peer_id: int,
        cer_id: str,
    ) -> VPNSubscription | None:
        user = await self.get_or_create_vk_user(peer_id)
        subscriptions = await self.get_user_subscriptions(user)

        for subscription in subscriptions:
            if subscription.cer_id == cer_id:
                return subscription

        return None

    async def show_android_instruction(
        self,
        peer_id: int,
        cer_id: str,
    ):
        subscription = await self.find_subscription_for_peer(
            peer_id=peer_id,
            cer_id=cer_id,
        )

        if not subscription:
            await self.send_message(
                peer_id=peer_id,
                message="Подписка не найдена.",
                keyboard=main_keyboard(),
            )
            return

        if not is_subscription_active(subscription):
            await self.send_message(
                peer_id=peer_id,
                message=(
                    "Эта подписка не активна.\n\n"
                    "Продлите подписку, чтобы использовать инструкции подключения."
                ),
                keyboard=profile_back_keyboard(),
            )
            return

        await self.send_message(
            peer_id=peer_id,
            message=(
                "🤖 Инструкция Android\n\n"
                f"Подписка: {subscription.cer_id}\n\n"
                "1. Установите strongSwan VPN Client:\n"
                "Откройте Google Play и установите приложение. Или скачайте strongSwan.apk напрямую по ссылке ниже 👇\n\n"
                "2. Загрузите профиль подключения.\n\n"
                "3. Введите пароль от сертификата:\n"
                "123456789\n\n"
                "4. Выберете СЕРТИФИКАТ VPN ИЛИ ПРИЛОЖЕНИЯ и нажмите ОК\n\n"
                "5. ИМЯ СЕРТИФИКАТА оставьте без изменений и нажмите ОК\n\n"
                "6. Чек-боксом будет выбран ваш сертификат, нажмите ВЫБРАТЬ\n\n"
                "7. В правом верхнем углу нажмите IMPORT\n\n"
                "8. В приложении нажмите на профиль чтобы подключиться"
            ),
            keyboard=android_instruction_keyboard(cer_id),
        )

    async def show_ios_instruction(
        self,
        peer_id: int,
        cer_id: str,
    ):
        subscription = await self.find_subscription_for_peer(
            peer_id=peer_id,
            cer_id=cer_id,
        )

        if not subscription:
            await self.send_message(
                peer_id=peer_id,
                message="Подписка не найдена.",
                keyboard=main_keyboard(),
            )
            return

        if not is_subscription_active(subscription):
            await self.send_message(
                peer_id=peer_id,
                message=(
                    "Эта подписка не активна.\n\n"
                    "Продлите подписку, чтобы использовать инструкции подключения."
                ),
                keyboard=profile_back_keyboard(),
            )
            return

        await self.send_message(
            peer_id=peer_id,
            message=(
                "🍎 Инструкция iOS\n\n"
                f"Подписка: {subscription.cer_id}\n\n"
                "1. Скачайте сертификат подключения.\n\n"
                "2. Откройте файл на iPhone.\n\n"
                "3. Установите профиль в настройках iOS.\n\n"
                "4. Введите пароль:\n"
                "123456789\n\n"
                "5. Подключитесь в настройках VPN."
            ),
            keyboard=ios_instruction_keyboard(cer_id),
        )

    async def send_android_profile(
        self,
        peer_id: int,
        cer_id: str | None,
    ):
        if not cer_id:
            await self.send_message(
                peer_id=peer_id,
                message="Не удалось определить подписку.",
                keyboard=profile_back_keyboard(),
            )
            return

        subscription = await self.find_subscription_for_peer(
            peer_id=peer_id,
            cer_id=cer_id,
        )

        if not subscription or not is_subscription_active(subscription):
            await self.send_message(
                peer_id=peer_id,
                message="Подписка не найдена или не активна.",
                keyboard=profile_back_keyboard(),
            )
            return

        profile_path = self.find_android_profile_file(cer_id)

        if not profile_path:
            if not subscription.cert_path:
                await self.send_message(
                    peer_id=peer_id,
                    message="❌ Файл сертификата .p12 не найден в базе.",
                    keyboard=profile_back_keyboard(),
                )
                return

            try:
                profile_path = create_strongswan_profile(
                    cer_id=subscription.cer_id,
                    p12_path=subscription.cert_path,
                )
            except FileNotFoundError:
                await self.send_message(
                    peer_id=peer_id,
                    message="❌ Файл сертификата .p12 не найден на сервере.",
                    keyboard=profile_back_keyboard(),
                )
                return
            except Exception as error:
                await self.send_message(
                    peer_id=peer_id,
                    message=(
                        "❌ Не удалось создать Android-профиль .sswan.\n\n"
                        f"Ошибка: {error}"
                    ),
                    keyboard=profile_back_keyboard(),
                )
                return

        await self.send_document_file(
            peer_id=peer_id,
            file_path=profile_path,
            title=f"{cer_id}.sswan",
            message=(
                "🤖 Android-профиль подключения\n\n"
                "Откройте этот файл через приложение StrongSwan."
            ),
        )

    async def send_ios_p12(
        self,
        peer_id: int,
        cer_id: str | None,
    ):
        if not cer_id:
            await self.send_message(
                peer_id=peer_id,
                message="Не удалось определить подписку.",
                keyboard=profile_back_keyboard(),
            )
            return

        subscription = await self.find_subscription_for_peer(
            peer_id=peer_id,
            cer_id=cer_id,
        )

        if not subscription or not is_subscription_active(subscription):
            await self.send_message(
                peer_id=peer_id,
                message="Подписка не найдена или не активна.",
                keyboard=profile_back_keyboard(),
            )
            return

        cert_path = resolve_project_path(subscription.cert_path)

        if not cert_path or not cert_path.exists():
            await self.send_message(
                peer_id=peer_id,
                message="❌ Файл сертификата .p12 не найден на сервере.",
                keyboard=profile_back_keyboard(),
            )
            return

        await self.send_document_file(
            peer_id=peer_id,
            file_path=cert_path,
            title=f"{cer_id}.p12",
            message=(
                "🍎 Сертификат подключения для iOS\n\n"
                "Пароль для импорта:\n"
                "123456789"
            ),
        )

    async def send_ca_cert(
        self,
        peer_id: int,
    ):
        ca_path = resolve_project_path(VK_CA_CERT_PATH)

        if not ca_path or not ca_path.exists():
            await self.send_message(
                peer_id=peer_id,
                message="❌ CA-сертификат не найден на сервере.",
                keyboard=profile_back_keyboard(),
            )
            return

        await self.send_document_file(
            peer_id=peer_id,
            file_path=ca_path,
            title=ca_path.name,
            message="📄 CA-сертификат для установки.",
        )

    async def send_android_video(
        self,
        peer_id: int,
    ):
        video_path = resolve_project_path(VK_ANDROID_VIDEO_PATH)

        if not video_path or not video_path.exists():
            await self.send_message(
                peer_id=peer_id,
                message="❌ Видео-инструкция Android не найдена на сервере.",
                keyboard=profile_back_keyboard(),
            )
            return

        await self.send_document_file(
            peer_id=peer_id,
            file_path=video_path,
            title=video_path.name,
            message="🎥 Видео-инструкция Android",
        )

    async def send_ios_video(
        self,
        peer_id: int,
    ):
        video_path = resolve_project_path(VK_IOS_VIDEO_PATH)

        if not video_path or not video_path.exists():
            await self.send_message(
                peer_id=peer_id,
                message="❌ Видео-инструкция iOS не найдена на сервере.",
                keyboard=profile_back_keyboard(),
            )
            return

        await self.send_document_file(
            peer_id=peer_id,
            file_path=video_path,
            title=video_path.name,
            message="🎥 Видео-инструкция iOS",
        )

    async def show_tariffs(self, peer_id: int):
        lines = ["💳 Тарифы\n"]

        for tariff in TARIFFS.values():
            lines.append(
                f"• {tariff['title']} — {tariff['amount']} ₽"
            )

        lines.append("")
        lines.append("Выберите тариф кнопкой ниже:")

        await self.send_message(
            peer_id=peer_id,
            message="\n".join(lines),
            keyboard=tariffs_keyboard(),
        )

    async def handle_payload(
        self,
        peer_id: int,
        payload: dict[str, Any],
    ):
        action = payload.get("action")

        if action == "profile":
            await self.show_profile(peer_id)
            return

        if action == "android_instruction":
            cer_id = payload.get("cer_id")

            if not cer_id:
                await self.send_message(
                    peer_id=peer_id,
                    message="Не удалось определить подписку.",
                    keyboard=main_keyboard(),
                )
                return

            await self.show_android_instruction(
                peer_id=peer_id,
                cer_id=cer_id,
            )
            return

        if action == "ios_instruction":
            cer_id = payload.get("cer_id")

            if not cer_id:
                await self.send_message(
                    peer_id=peer_id,
                    message="Не удалось определить подписку.",
                    keyboard=main_keyboard(),
                )
                return

            await self.show_ios_instruction(
                peer_id=peer_id,
                cer_id=cer_id,
            )
            return

        if action == "send_android_profile":
            cer_id = payload.get("cer_id")
            await self.send_android_profile(peer_id, cer_id)
            return

        if action == "send_ios_p12":
            cer_id = payload.get("cer_id")
            await self.send_ios_p12(peer_id, cer_id)
            return

        if action == "send_ca_cert":
            await self.send_ca_cert(peer_id)
            return

        if action == "send_android_video":
            await self.send_android_video(peer_id)
            return

        if action == "send_ios_video":
            await self.send_ios_video(peer_id)
            return

        if action == "buy_tariff":
            tariff_code = payload.get("tariff_code")

            if tariff_code not in TARIFFS:
                await self.send_message(
                    peer_id=peer_id,
                    message="Тариф не найден.",
                    keyboard=main_keyboard(),
                )
                return

            await self.start_vk_order_flow(
                peer_id=peer_id,
                tariff_code=tariff_code,
            )
            return

        if action == "renew_subscription":
            tariff_code = payload.get("tariff_code")
            cer_id = payload.get("cer_id")

            if tariff_code not in TARIFFS or not cer_id:
                await self.send_message(
                    peer_id=peer_id,
                    message="Не удалось выбрать подписку для продления.",
                    keyboard=main_keyboard(),
                )
                return

            self.pending_payments[peer_id] = {
                "action": "renew",
                "tariff_code": tariff_code,
                "cer_id": cer_id,
            }

            await self.send_message(
                peer_id=peer_id,
                message=(
                    "📧 Введите email для отправки чека.\n\n"
                    "Например: user@example.com"
                ),
                keyboard=None,
            )
            return

        if action == "open_tariffs":
            await self.show_tariffs(peer_id)
            return

        await self.send_message(
            peer_id=peer_id,
            message="Неизвестное действие.",
            keyboard=main_keyboard(),
        )

    async def start_vk_order_flow(
        self,
        peer_id: int,
        tariff_code: str,
    ):
        async with AsyncSessionLocal() as session:
            user = await get_or_create_platform_user(
                session=session,
                platform="vk",
                external_id=peer_id,
            )

            active_subscriptions = await get_active_platform_subscriptions(
                session=session,
                user=user,
            )

        if len(active_subscriptions) == 0:
            self.pending_payments[peer_id] = {
                "action": "buy",
                "tariff_code": tariff_code,
                "cer_id": None,
            }

            await self.send_message(
                peer_id=peer_id,
                message=(
                    "📧 Введите email для отправки чека.\n\n"
                    "Например: user@example.com"
                ),
                keyboard=None,
            )
            return

        if len(active_subscriptions) == 1:
            self.pending_payments[peer_id] = {
                "action": "renew",
                "tariff_code": tariff_code,
                "cer_id": active_subscriptions[0].cer_id,
            }

            await self.send_message(
                peer_id=peer_id,
                message=(
                    "📧 Введите email для отправки чека.\n\n"
                    "Подписка будет продлена.\n\n"
                    "Например: user@example.com"
                ),
                keyboard=None,
            )
            return

        await self.send_message(
            peer_id=peer_id,
            message=(
                "🔄 У вас несколько активных подписок.\n\n"
                "Выберите, какую подписку продлить:"
            ),
            keyboard=renew_subscriptions_keyboard(
                tariff_code=tariff_code,
                subscriptions=active_subscriptions,
            ),
        )

    async def process_payment_email(
        self,
        peer_id: int,
        email: str,
    ):
        email = email.strip().lower()

        if not EMAIL_RE.match(email):
            await self.send_message(
                peer_id=peer_id,
                message=(
                    "Некорректный email.\n\n"
                    "Введите email ещё раз, например:\n"
                    "user@example.com"
                ),
                keyboard=None,
            )
            return

        pending = self.pending_payments.pop(peer_id)

        await self.send_message(
            peer_id=peer_id,
            message="⏳ Создаю заказ...",
            keyboard=None,
        )

        try:
            payment_url = await self.create_vk_payment(
                peer_id=peer_id,
                action=pending["action"],
                tariff_code=pending["tariff_code"],
                cer_id=pending.get("cer_id"),
                customer_email=email,
            )
        except Exception as error:
            await self.send_message(
                peer_id=peer_id,
                message=(
                    "❌ Не удалось создать оплату.\n\n"
                    f"Ошибка: {error}"
                ),
                keyboard=main_keyboard(),
            )
            return

        try:
            await self.send_message(
                peer_id=peer_id,
                message=(
                    "🧾 Заказ создан.\n\n"
                    "Нажмите кнопку ниже для оплаты."
                ),
                keyboard=payment_keyboard(payment_url),
            )
        except Exception:
            await self.send_message(
                peer_id=peer_id,
                message=(
                    "🧾 Заказ создан.\n\n"
                    "Ссылка для оплаты:\n"
                    f"{payment_url}"
                ),
                keyboard=main_keyboard(),
            )

    async def create_vk_payment(
        self,
        peer_id: int,
        action: str,
        tariff_code: str,
        cer_id: str | None,
        customer_email: str,
    ) -> str:
        async with AsyncSessionLocal() as session:
            user = await get_or_create_platform_user(
                session=session,
                platform="vk",
                external_id=peer_id,
            )

            if action == "buy":
                subscription = await create_platform_pending_subscription(
                    session=session,
                    user=user,
                    platform="vk",
                    external_id=peer_id,
                )

                order = await create_platform_order(
                    session=session,
                    user=user,
                    platform="vk",
                    external_id=peer_id,
                    tariff_code=tariff_code,
                    action="buy",
                    subscription_id=subscription.id,
                    cer_id=subscription.cer_id,
                    customer_email=customer_email,
                )

                manager = MikroTikManager(config.mikrotik)
                cert_path = await manager.certs.create_cert(subscription.cer_id)

                subscription = await mark_platform_cert_created(
                    session=session,
                    subscription=subscription,
                    cert_path=cert_path,
                )

            elif action == "renew":
                order = await create_platform_order(
                    session=session,
                    user=user,
                    platform="vk",
                    external_id=peer_id,
                    tariff_code=tariff_code,
                    action="renew",
                    subscription_id=None,
                    cer_id=cer_id,
                    customer_email=customer_email,
                )

            else:
                raise ValueError("unknown_action")

            payment_data = await init_tbank_payment(order)

            payment_url = payment_data.get("PaymentURL")

            if not payment_url:
                raise RuntimeError("Банк не вернул ссылку на оплату")

            order = await attach_payment_to_order(
                session=session,
                order_id=order.id,
                payment_id=str(payment_data.get("PaymentId")),
                payment_url=payment_url,
                payment_status=payment_data.get("Status"),
            )

            return order.payment_url

    async def show_link_code(self, peer_id: int):
        async with AsyncSessionLocal() as session:
            link_code = await create_account_link_code(
                session=session,
                source_platform="vk",
                source_external_id=peer_id,
            )

        await self.send_message(
            peer_id=peer_id,
            message=(
                "🔗 Привязка аккаунта\n\n"
                "Ваш код привязки:\n\n"
                f"{link_code.code}\n\n"
                "Введите этот код в Telegram-боте, чтобы связать VK и Telegram.\n\n"
                "Код действует 10 минут."
            ),
            keyboard=main_keyboard(),
        )

    async def process_link_code(
        self,
        peer_id: int,
        code: str,
    ):
        async with AsyncSessionLocal() as session:
            result = await apply_link_code(
                session=session,
                target_platform="vk",
                target_external_id=peer_id,
                code=code,
            )

        status = result["status"]

        if status == "invalid_code":
            await self.send_message(
                peer_id=peer_id,
                message=(
                    "❌ Код не найден или уже истёк.\n\n"
                    "Проверьте код или получите новый код привязки."
                ),
                keyboard=main_keyboard(),
            )
            return

        if status == "same_platform":
            await self.send_message(
                peer_id=peer_id,
                message=(
                    "⚠️ Этот код был создан в VK.\n\n"
                    "Введите его в Telegram-боте, чтобы привязать Telegram."
                ),
                keyboard=main_keyboard(),
            )
            return

        if status == "already_linked":
            await self.send_message(
                peer_id=peer_id,
                message=(
                    "✅ Этот VK уже привязан к аккаунту.\n\n"
                    "Теперь вы можете смотреть профиль и подписки через VK-бота."
                ),
                keyboard=main_keyboard(),
            )
            return

        if status == "linked":
            await self.send_message(
                peer_id=peer_id,
                message=(
                    "✅ VK успешно привязан к аккаунту.\n\n"
                    "Теперь VK-бот и Telegram-бот будут работать с одним профилем."
                ),
                keyboard=main_keyboard(),
            )
            return

        if status == "need_merge":
            async with AsyncSessionLocal() as session:
                merge_request = await create_account_merge_request(
                    session=session,
                    source_user_id=result["source_user_id"],
                    target_user_id=result["target_user_id"],
                    link_code_id=result["link_code_id"],
                    target_platform="vk",
                    target_external_id=peer_id,
                )

                source_stats = await get_user_stats(
                    session=session,
                    user_id=result["source_user_id"],
                )

                target_stats = await get_user_stats(
                    session=session,
                    user_id=result["target_user_id"],
                )

            await self.send_message(
                peer_id=peer_id,
                message=(
                    "⚠️ Найдены два разных профиля.\n\n"
                    "Профиль, который создал код:\n"
                    f"Подписок: {source_stats['subscriptions_count']}\n"
                    f"Заказов: {source_stats['orders_count']}\n\n"
                    "Текущий VK-профиль:\n"
                    f"Подписок: {target_stats['subscriptions_count']}\n"
                    f"Заказов: {target_stats['orders_count']}\n\n"
                    "Объединить профили?\n\n"
                    "После объединения оба бота будут показывать одни и те же подписки."
                ),
                keyboard=merge_confirm_keyboard(),
            )
            return

        await self.send_message(
            peer_id=peer_id,
            message="Неизвестный результат привязки.",
            keyboard=main_keyboard(),
        )

    async def confirm_merge(self, peer_id: int):
        async with AsyncSessionLocal() as session:
            merge_request = await get_pending_merge_request(
                session=session,
                target_platform="vk",
                target_external_id=peer_id,
            )

            if not merge_request:
                await self.send_message(
                    peer_id=peer_id,
                    message=(
                        "Заявка на объединение не найдена или уже истекла.\n\n"
                        "Получите новый код привязки."
                    ),
                    keyboard=main_keyboard(),
                )
                return

            try:
                user = await approve_merge_request(
                    session=session,
                    merge_request=merge_request,
                )
            except Exception as error:
                await self.send_message(
                    peer_id=peer_id,
                    message=(
                        "❌ Не удалось объединить профили.\n\n"
                        f"Ошибка: {error}"
                    ),
                    keyboard=main_keyboard(),
                )
                return

        await self.send_message(
            peer_id=peer_id,
            message=(
                "✅ Профили успешно объединены.\n\n"
                "Теперь VK-бот и Telegram-бот будут работать с одним аккаунтом.\n\n"
                f"Основной профиль ID: {user.id}"
            ),
            keyboard=main_keyboard(),
        )

    async def cancel_merge(self, peer_id: int):
        async with AsyncSessionLocal() as session:
            merge_request = await get_pending_merge_request(
                session=session,
                target_platform="vk",
                target_external_id=peer_id,
            )

            if not merge_request:
                await self.send_message(
                    peer_id=peer_id,
                    message="Активной заявки на объединение нет.",
                    keyboard=main_keyboard(),
                )
                return

            await cancel_merge_request(
                session=session,
                merge_request=merge_request,
            )

        await self.send_message(
            peer_id=peer_id,
            message=(
                "Ок, профили оставлены отдельно.\n\n"
                "Код привязки больше не активен."
            ),
            keyboard=main_keyboard(),
        )
    async def show_support(self, peer_id: int):
        await self.send_message(
            peer_id=peer_id,
            message=(
                "💬 Поддержка\n\n"
                "Напишите ваш вопрос одним сообщением.\n"
                "Позже мы подключим пересылку обращений администратору."
            ),
            keyboard=main_keyboard(),
        )

    async def send_message(
        self,
        peer_id: int,
        message: str,
        keyboard: dict[str, Any] | None = None,
        attachment: str | None = None,
    ):
        params = {
            "peer_id": peer_id,
            "message": message,
            "random_id": random.randint(1, 2_147_483_647),
        }

        if keyboard:
            params["keyboard"] = json.dumps(
                keyboard,
                ensure_ascii=False,
            )

        if attachment:
            params["attachment"] = attachment

        await self.api_call("messages.send", params)

    async def upload_message_document(
        self,
        peer_id: int,
        file_path: str | Path,
        title: str | None = None,
    ) -> str:
        file_path = resolve_project_path(file_path)

        if not file_path or not file_path.exists():
            raise FileNotFoundError(f"Файл не найден: {file_path}")

        upload_server = await self.api_call(
            "docs.getMessagesUploadServer",
            {
                "peer_id": peer_id,
                "type": "doc",
            },
        )

        upload_url = upload_server["upload_url"]

        form = aiohttp.FormData()

        with file_path.open("rb") as file:
            form.add_field(
                "file",
                file,
                filename=title or file_path.name,
                content_type="application/octet-stream",
            )

            async with self.session.post(
                upload_url,
                data=form,
                timeout=aiohttp.ClientTimeout(total=120),
            ) as response:
                upload_result = await response.json(content_type=None)

        if "file" not in upload_result:
            raise RuntimeError(f"VK upload failed: {upload_result}")

        saved = await self.api_call(
            "docs.save",
            {
                "file": upload_result["file"],
                "title": title or file_path.name,
            },
        )

        if isinstance(saved, dict) and "doc" in saved:
            doc = saved["doc"]
        elif isinstance(saved, dict) and "items" in saved and saved["items"]:
            doc = saved["items"][0]
        elif isinstance(saved, list) and saved:
            doc = saved[0]
        else:
            raise RuntimeError(f"VK docs.save unexpected response: {saved}")

        attachment = f"doc{doc['owner_id']}_{doc['id']}"

        if doc.get("access_key"):
            attachment += f"_{doc['access_key']}"

        return attachment

    async def send_document_file(
        self,
        peer_id: int,
        file_path: str | Path,
        title: str,
        message: str,
    ):
        try:
            attachment = await self.upload_message_document(
                peer_id=peer_id,
                file_path=file_path,
                title=title,
            )

            await self.send_message(
                peer_id=peer_id,
                message=message,
                attachment=attachment,
                keyboard=profile_back_keyboard(),
            )

        except Exception as error:
            await self.send_message(
                peer_id=peer_id,
                message=(
                    "❌ Не удалось отправить файл.\n\n"
                    f"Ошибка: {error}"
                ),
                keyboard=profile_back_keyboard(),
            )

    def find_android_profile_file(self, cer_id: str) -> Path | None:
        candidates = [
            PROJECT_ROOT / "storage" / "profiles" / f"{cer_id}.sswan",
            PROJECT_ROOT / "storage" / "strongswan" / f"{cer_id}.sswan",
            PROJECT_ROOT / "storage" / "android" / f"{cer_id}.sswan",
        ]

        for candidate in candidates:
            if candidate.exists():
                return candidate

        matches = list((PROJECT_ROOT / "storage").glob(f"**/{cer_id}*.sswan"))

        if matches:
            return matches[0]

        return None

def main_keyboard() -> dict[str, Any]:
    return {
        "one_time": False,
        "inline": False,
        "buttons": [
            [
                {
                    "action": {
                        "type": "text",
                        "label": "👤 Профиль",
                    },
                    "color": "primary",
                },
                {
                    "action": {
                        "type": "text",
                        "label": "💳 Тарифы",
                    },
                    "color": "primary",
                },
            ],
            [
                {
                    "action": {
                        "type": "text",
                        "label": "🔗 Привязка",
                    },
                    "color": "secondary",
                },
                {
                    "action": {
                        "type": "text",
                        "label": "💬 Поддержка",
                    },
                    "color": "secondary",
                },
            ],
        ],
    }

def profile_empty_keyboard() -> dict[str, Any]:
    return {
        "inline": True,
        "buttons": [
            [
                {
                    "action": {
                        "type": "text",
                        "label": "💳 Выбрать тариф",
                        "payload": json.dumps(
                            {
                                "action": "open_tariffs",
                            },
                            ensure_ascii=False,
                        ),
                    },
                    "color": "primary",
                }
            ],
            [
                {
                    "action": {
                        "type": "text",
                        "label": "Меню",
                    },
                    "color": "secondary",
                }
            ],
        ],
    }


def profile_subscriptions_keyboard(subscriptions) -> dict[str, Any]:
    buttons = []

    for index, subscription in enumerate(subscriptions, start=1):
        if not is_subscription_active(subscription):
            continue

        buttons.append(
            [
                {
                    "action": {
                        "type": "text",
                        "label": f"🤖 Android #{index}",
                        "payload": json.dumps(
                            {
                                "action": "android_instruction",
                                "cer_id": subscription.cer_id,
                            },
                            ensure_ascii=False,
                        ),
                    },
                    "color": "primary",
                },
                {
                    "action": {
                        "type": "text",
                        "label": f"🍎 iOS #{index}",
                        "payload": json.dumps(
                            {
                                "action": "ios_instruction",
                                "cer_id": subscription.cer_id,
                            },
                            ensure_ascii=False,
                        ),
                    },
                    "color": "primary",
                },
            ]
        )

    buttons.append(
        [
            {
                "action": {
                    "type": "text",
                    "label": "💳 Тарифы",
                },
                "color": "secondary",
            },
            {
                "action": {
                    "type": "text",
                    "label": "Меню",
                },
                "color": "secondary",
            },
        ]
    )

    return {
        "inline": True,
        "buttons": buttons,
    }


def profile_back_keyboard() -> dict[str, Any]:
    return {
        "inline": True,
        "buttons": [
            [
                {
                    "action": {
                        "type": "text",
                        "label": "👤 Профиль",
                        "payload": json.dumps(
                            {
                                "action": "profile",
                            },
                            ensure_ascii=False,
                        ),
                    },
                    "color": "primary",
                }
            ],
            [
                {
                    "action": {
                        "type": "text",
                        "label": "Меню",
                    },
                    "color": "secondary",
                }
            ],
        ],
    }


def android_instruction_keyboard(cer_id: str) -> dict[str, Any]:
    return {
        "inline": True,
        "buttons": [
            [
                {
                    "action": {
                        "type": "open_link",
                        "label": "📦 Скачать APK",
                        "link": "https://mymayak.ru/downloads/strongswan.apk",
                    }
                }
            ],
            [
                {
                    "action": {
                        "type": "text",
                        "label": "⚡ Загрузить профиль",
                        "payload": json.dumps(
                            {
                                "action": "send_android_profile",
                                "cer_id": cer_id,
                            },
                            ensure_ascii=False,
                        ),
                    },
                    "color": "primary",
                }
            ],
            [
                {
                    "action": {
                        "type": "text",
                        "label": "🎥 Видео-инструкция",
                        "payload": json.dumps(
                            {
                                "action": "send_android_video",
                            },
                            ensure_ascii=False,
                        ),
                    },
                    "color": "secondary",
                }
            ],
            [
                {
                    "action": {
                        "type": "text",
                        "label": "👤 Назад в профиль",
                        "payload": json.dumps(
                            {
                                "action": "profile",
                            },
                            ensure_ascii=False,
                        ),
                    },
                    "color": "secondary",
                }
            ],
        ],
    }

def ios_instruction_keyboard(cer_id: str) -> dict[str, Any]:
    return {
        "inline": True,
        "buttons": [
            [
                {
                    "action": {
                        "type": "text",
                        "label": "📄 Скачать .p12",
                        "payload": json.dumps(
                            {
                                "action": "send_ios_p12",
                                "cer_id": cer_id,
                            },
                            ensure_ascii=False,
                        ),
                    },
                    "color": "primary",
                }
            ],
            [
                {
                    "action": {
                        "type": "text",
                        "label": "📄 Скачать CA",
                        "payload": json.dumps(
                            {
                                "action": "send_ca_cert",
                            },
                            ensure_ascii=False,
                        ),
                    },
                    "color": "secondary",
                }
            ],
            [
                {
                    "action": {
                        "type": "text",
                        "label": "🎥 Видео-инструкция",
                        "payload": json.dumps(
                            {
                                "action": "send_ios_video",
                            },
                            ensure_ascii=False,
                        ),
                    },
                    "color": "secondary",
                }
            ],
            [
                {
                    "action": {
                        "type": "text",
                        "label": "👤 Назад в профиль",
                        "payload": json.dumps(
                            {
                                "action": "profile",
                            },
                            ensure_ascii=False,
                        ),
                    },
                    "color": "secondary",
                }
            ],
        ],
    }

def tariffs_keyboard() -> dict[str, Any]:
    buttons = []

    for code, tariff in TARIFFS.items():
        buttons.append(
            [
                {
                    "action": {
                        "type": "text",
                        "label": f"{tariff['title']} — {tariff['amount']} ₽",
                        "payload": json.dumps(
                            {
                                "action": "buy_tariff",
                                "tariff_code": code,
                            },
                            ensure_ascii=False,
                        ),
                    },
                    "color": "primary",
                }
            ]
        )

    buttons.append(
        [
            {
                "action": {
                    "type": "text",
                    "label": "Меню",
                },
                "color": "secondary",
            }
        ]
    )

    return {
        "one_time": False,
        "inline": False,
        "buttons": buttons,
    }


def renew_subscriptions_keyboard(
    tariff_code: str,
    subscriptions,
) -> dict[str, Any]:
    buttons = []

    for index, subscription in enumerate(subscriptions, start=1):
        buttons.append(
            [
                {
                    "action": {
                        "type": "text",
                        "label": f"Продлить подписку #{index}",
                        "payload": json.dumps(
                            {
                                "action": "renew_subscription",
                                "tariff_code": tariff_code,
                                "cer_id": subscription.cer_id,
                            },
                            ensure_ascii=False,
                        ),
                    },
                    "color": "primary",
                }
            ]
        )

    buttons.append(
        [
            {
                "action": {
                    "type": "text",
                    "label": "Меню",
                },
                "color": "secondary",
            }
        ]
    )

    return {
        "one_time": False,
        "inline": False,
        "buttons": buttons,
    }


def payment_keyboard(payment_url: str) -> dict[str, Any]:
    return {
        "inline": True,
        "buttons": [
            [
                {
                    "action": {
                        "type": "open_link",
                        "label": "💳 Оплатить",
                        "link": payment_url,
                    },
                }
            ],
            [
                {
                    "action": {
                        "type": "text",
                        "label": "Меню",
                    },
                    "color": "secondary",
                }
            ],
        ],
    }

def merge_confirm_keyboard() -> dict[str, Any]:
    return {
        "one_time": True,
        "inline": False,
        "buttons": [
            [
                {
                    "action": {
                        "type": "text",
                        "label": "✅ Да, объединить",
                    },
                    "color": "positive",
                },
            ],
            [
                {
                    "action": {
                        "type": "text",
                        "label": "❌ Нет, оставить отдельно",
                    },
                    "color": "negative",
                },
            ],
        ],
    }
async def main():
    bot = VKBot()

    try:
        await bot.start()
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())