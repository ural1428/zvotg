import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import (
    AccountLinkCode,
    AccountMergeRequest,
    Order,
    User,
    VPNSubscription,
)


LINK_CODE_TTL_MINUTES = 10


def generate_link_code() -> str:
    return str(secrets.randbelow(900000) + 100000)


def normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


async def get_user_by_platform_id(
    session: AsyncSession,
    platform: str,
    external_id: int,
) -> User | None:
    if platform == "tg":
        result = await session.execute(
            select(User).where(
                User.telegram_id == external_id,
                User.is_merged.is_(False),
            )
        )
        return result.scalar_one_or_none()

    if platform == "vk":
        result = await session.execute(
            select(User).where(
                User.vk_peer_id == external_id,
                User.is_merged.is_(False),
            )
        )
        return result.scalar_one_or_none()

    raise ValueError("Unknown platform")


async def get_or_create_platform_user(
    session: AsyncSession,
    platform: str,
    external_id: int,
) -> User:
    user = await get_user_by_platform_id(
        session=session,
        platform=platform,
        external_id=external_id,
    )

    if user:
        return user

    if platform == "tg":
        user = User(
            telegram_id=external_id,
            primary_platform="tg",
            primary_external_id=external_id,
        )
    elif platform == "vk":
        user = User(
            vk_peer_id=external_id,
            primary_platform="vk",
            primary_external_id=external_id,
        )
    else:
        raise ValueError("Unknown platform")

    session.add(user)
    await session.commit()
    await session.refresh(user)

    return user


async def create_account_link_code(
    session: AsyncSession,
    source_platform: str,
    source_external_id: int,
) -> AccountLinkCode:
    user = await get_or_create_platform_user(
        session=session,
        platform=source_platform,
        external_id=source_external_id,
    )

    now = datetime.now(timezone.utc)

    result = await session.execute(
        select(AccountLinkCode).where(
            AccountLinkCode.source_user_id == user.id,
            AccountLinkCode.used_at.is_(None),
        )
    )

    for old_code in result.scalars().all():
        old_code.used_at = now

    while True:
        code = generate_link_code()

        existing = await session.execute(
            select(AccountLinkCode).where(AccountLinkCode.code == code)
        )

        if not existing.scalar_one_or_none():
            break

    link_code = AccountLinkCode(
        code=code,
        source_user_id=user.id,
        source_platform=source_platform,
        source_external_id=source_external_id,
        expires_at=now + timedelta(minutes=LINK_CODE_TTL_MINUTES),
    )

    session.add(link_code)

    await session.commit()
    await session.refresh(link_code)

    return link_code


async def find_active_link_code(
    session: AsyncSession,
    code: str,
) -> AccountLinkCode | None:
    now = datetime.now(timezone.utc)

    result = await session.execute(
        select(AccountLinkCode).where(
            AccountLinkCode.code == code.strip(),
            AccountLinkCode.used_at.is_(None),
            AccountLinkCode.expires_at > now,
        )
    )

    return result.scalar_one_or_none()


async def get_user_by_id(
    session: AsyncSession,
    user_id: int,
) -> User | None:
    result = await session.execute(
        select(User).where(User.id == user_id)
    )

    return result.scalar_one_or_none()


async def get_user_subscription_count(
    session: AsyncSession,
    user_id: int,
) -> int:
    result = await session.execute(
        select(VPNSubscription.id).where(
            VPNSubscription.user_id == user_id
        )
    )

    return len(result.all())


async def get_user_order_count(
    session: AsyncSession,
    user_id: int,
) -> int:
    result = await session.execute(
        select(Order.id).where(
            Order.user_id == user_id
        )
    )

    return len(result.all())


async def user_has_data(
    session: AsyncSession,
    user_id: int,
) -> bool:
    subscriptions_count = await get_user_subscription_count(
        session=session,
        user_id=user_id,
    )

    orders_count = await get_user_order_count(
        session=session,
        user_id=user_id,
    )

    return subscriptions_count > 0 or orders_count > 0


async def mark_link_code_used(
    session: AsyncSession,
    link_code: AccountLinkCode,
) -> None:
    link_code.used_at = datetime.now(timezone.utc)
    await session.commit()


async def attach_platform_to_user(
    session: AsyncSession,
    user: User,
    platform: str,
    external_id: int,
) -> User:
    if platform == "tg":
        user.telegram_id = external_id
    elif platform == "vk":
        user.vk_peer_id = external_id
    else:
        raise ValueError("Unknown platform")

    await session.commit()
    await session.refresh(user)

    return user


async def mark_user_merged(
    session: AsyncSession,
    source_user: User,
    target_user: User,
) -> None:
    source_user.is_merged = True
    source_user.merged_into_user_id = target_user.id

    if source_user.telegram_id == target_user.telegram_id:
        source_user.telegram_id = None

    if source_user.vk_peer_id == target_user.vk_peer_id:
        source_user.vk_peer_id = None


async def apply_link_code(
    session: AsyncSession,
    target_platform: str,
    target_external_id: int,
    code: str,
) -> dict:
    """
    target_platform/target_external_id — это бот, куда пользователь ввёл код.
    Например:
    - код создан в Telegram
    - пользователь ввёл его в VK
    - target_platform = "vk"
    - target_external_id = vk_peer_id

    Возвращает dict со status:
    - linked
    - already_linked
    - same_platform
    - invalid_code
    - need_merge
    """

    link_code = await find_active_link_code(
        session=session,
        code=code,
    )

    if not link_code:
        return {
            "status": "invalid_code",
        }

    if link_code.source_platform == target_platform:
        return {
            "status": "same_platform",
            "source_platform": link_code.source_platform,
        }

    source_user = await get_user_by_id(
        session=session,
        user_id=link_code.source_user_id,
    )

    if not source_user or source_user.is_merged:
        return {
            "status": "invalid_code",
        }

    target_user = await get_user_by_platform_id(
        session=session,
        platform=target_platform,
        external_id=target_external_id,
    )

    if target_platform == "tg":
        already_attached_id = source_user.telegram_id
    elif target_platform == "vk":
        already_attached_id = source_user.vk_peer_id
    else:
        raise ValueError("Unknown platform")

    if already_attached_id == target_external_id:
        await mark_link_code_used(session, link_code)

        return {
            "status": "already_linked",
            "user_id": source_user.id,
        }

    # Если целевого пользователя ещё нет — просто привязываем платформу к source_user.
    if not target_user:
        await attach_platform_to_user(
            session=session,
            user=source_user,
            platform=target_platform,
            external_id=target_external_id,
        )

        await mark_link_code_used(session, link_code)

        return {
            "status": "linked",
            "user_id": source_user.id,
        }

    # Если VK/TG пользователь уже существует, но это тот же user.
    if target_user.id == source_user.id:
        await mark_link_code_used(session, link_code)

        return {
            "status": "already_linked",
            "user_id": source_user.id,
        }

    # Если целевой профиль пустой, можно безопасно присоединить его без вопроса.
    target_has_data = await user_has_data(
        session=session,
        user_id=target_user.id,
    )

    if not target_has_data:
        if target_platform == "tg":
            target_user.telegram_id = None
        elif target_platform == "vk":
            target_user.vk_peer_id = None

        await mark_user_merged(
            session=session,
            source_user=target_user,
            target_user=source_user,
        )

        await attach_platform_to_user(
            session=session,
            user=source_user,
            platform=target_platform,
            external_id=target_external_id,
        )

        await mark_link_code_used(session, link_code)

        return {
            "status": "linked",
            "user_id": source_user.id,
            "merged_empty_user_id": target_user.id,
        }

    # Если у второго профиля уже есть подписки/заказы,
    # автоматом не объединяем. На следующем этапе спросим пользователя.
    return {
        "status": "need_merge",
        "source_user_id": source_user.id,
        "target_user_id": target_user.id,
        "link_code_id": link_code.id,
    }

async def create_account_merge_request(
    session: AsyncSession,
    source_user_id: int,
    target_user_id: int,
    link_code_id: int | None,
    target_platform: str,
    target_external_id: int,
) -> AccountMergeRequest:
    now = datetime.now(timezone.utc)

    # Закрываем старые pending-заявки для этого VK/TG входа.
    result = await session.execute(
        select(AccountMergeRequest).where(
            AccountMergeRequest.target_platform == target_platform,
            AccountMergeRequest.target_external_id == target_external_id,
            AccountMergeRequest.status == "pending",
        )
    )

    for old_request in result.scalars().all():
        old_request.status = "expired"
        old_request.decided_at = now

    merge_request = AccountMergeRequest(
        source_user_id=source_user_id,
        target_user_id=target_user_id,
        link_code_id=link_code_id,
        target_platform=target_platform,
        target_external_id=target_external_id,
        status="pending",
        expires_at=now + timedelta(minutes=LINK_CODE_TTL_MINUTES),
    )

    session.add(merge_request)
    await session.commit()
    await session.refresh(merge_request)

    return merge_request


async def get_pending_merge_request(
    session: AsyncSession,
    target_platform: str,
    target_external_id: int,
) -> AccountMergeRequest | None:
    now = datetime.now(timezone.utc)

    result = await session.execute(
        select(AccountMergeRequest).where(
            AccountMergeRequest.target_platform == target_platform,
            AccountMergeRequest.target_external_id == target_external_id,
            AccountMergeRequest.status == "pending",
            AccountMergeRequest.expires_at > now,
        )
    )

    return result.scalar_one_or_none()


async def get_user_stats(
    session: AsyncSession,
    user_id: int,
) -> dict:
    subscriptions_count = await get_user_subscription_count(
        session=session,
        user_id=user_id,
    )

    orders_count = await get_user_order_count(
        session=session,
        user_id=user_id,
    )

    return {
        "subscriptions_count": subscriptions_count,
        "orders_count": orders_count,
    }


async def cancel_merge_request(
    session: AsyncSession,
    merge_request: AccountMergeRequest,
) -> None:
    now = datetime.now(timezone.utc)

    merge_request.status = "cancelled"
    merge_request.decided_at = now

    if merge_request.link_code_id:
        link_code = await get_link_code_by_id(
            session=session,
            link_code_id=merge_request.link_code_id,
        )

        if link_code and not link_code.used_at:
            link_code.used_at = now

    await session.commit()


async def get_link_code_by_id(
    session: AsyncSession,
    link_code_id: int,
) -> AccountLinkCode | None:
    result = await session.execute(
        select(AccountLinkCode).where(AccountLinkCode.id == link_code_id)
    )

    return result.scalar_one_or_none()


async def approve_merge_request(
    session: AsyncSession,
    merge_request: AccountMergeRequest,
) -> User:
    now = datetime.now(timezone.utc)

    source_user = await get_user_by_id(
        session=session,
        user_id=merge_request.source_user_id,
    )

    target_user = await get_user_by_id(
        session=session,
        user_id=merge_request.target_user_id,
    )

    if not source_user or not target_user:
        raise ValueError("Merge users not found")

    if source_user.is_merged:
        raise ValueError("Source user already merged")

    if target_user.is_merged:
        raise ValueError("Target user already merged")

    # Переносим Telegram ID, если он есть только у target.
    if source_user.telegram_id is None and target_user.telegram_id is not None:
        source_user.telegram_id = target_user.telegram_id
        target_user.telegram_id = None
    elif (
        source_user.telegram_id is not None
        and target_user.telegram_id is not None
        and source_user.telegram_id != target_user.telegram_id
    ):
        raise ValueError("Telegram ID conflict")

    # Переносим VK peer_id, если он есть только у target.
    if source_user.vk_peer_id is None and target_user.vk_peer_id is not None:
        source_user.vk_peer_id = target_user.vk_peer_id
        target_user.vk_peer_id = None
    elif (
        source_user.vk_peer_id is not None
        and target_user.vk_peer_id is not None
        and source_user.vk_peer_id != target_user.vk_peer_id
    ):
        raise ValueError("VK peer_id conflict")

    # Подписки target-профиля переносим в source-профиль.
    await session.execute(
        update(VPNSubscription)
        .where(VPNSubscription.user_id == target_user.id)
        .values(user_id=source_user.id)
    )

    # Заказы target-профиля переносим в source-профиль.
    await session.execute(
        update(Order)
        .where(Order.user_id == target_user.id)
        .values(user_id=source_user.id)
    )

    target_user.is_merged = True
    target_user.merged_into_user_id = source_user.id

    merge_request.status = "merged"
    merge_request.decided_at = now

    if merge_request.link_code_id:
        link_code = await get_link_code_by_id(
            session=session,
            link_code_id=merge_request.link_code_id,
        )

        if link_code and not link_code.used_at:
            link_code.used_at = now

    await session.commit()
    await session.refresh(source_user)

    return source_user