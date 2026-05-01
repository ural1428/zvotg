from app.repositories.users import (
    UserRepository,
)


class UserService:

    def __init__(
        self,
        users_repo: UserRepository,
    ):

        self.users_repo = users_repo

    async def get_or_create_user(
        self,
        telegram_id: int,
        username: str | None = None,
    ):

        user = await self.users_repo.get_by_telegram_id(
            telegram_id
        )

        if user:
            return user

        return await self.users_repo.create(
            telegram_id=telegram_id,
            username=username,
        )
