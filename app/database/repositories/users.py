from sqlalchemy import (
    select,
)

from app.repositories.base import (
    BaseRepository,
)

from app.database.models.user import (
    User,
)


class UserRepository(
    BaseRepository
):

    async def get_by_telegram_id(
        self,
        telegram_id: int,
    ):

        query = select(User).where(
            User.telegram_id == telegram_id
        )

        result = await self.session.execute(
            query
        )

        return result.scalar_one_or_none()

    async def create(
        self,
        telegram_id: int,
        username: str | None = None,
    ):

        user = User(
            telegram_id=telegram_id,
            username=username,
        )

        self.session.add(user)

        await self.session.commit()

        await self.session.refresh(user)

        return user
