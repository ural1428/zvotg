from app.integrations.mikrotik.manager import (
    MikroTikManager,
)

from app.database.repositories.certificates import (
    CertificateRepository,
)

from app.database.repositories.users import (
    UserRepository,
)


class VPNService:

    def __init__(
        self,
        mikrotik: MikroTikManager,
        certificate_repository: CertificateRepository,
        user_repository: UserRepository,
    ):

        self.mikrotik = mikrotik

        self.certificate_repository = (
            certificate_repository
        )

        self.user_repository = (
            user_repository
        )

    async def create_vpn(
        self,
        telegram_id: int,
        cert_id: int,
    ):

        user = await self.user_repository.get_by_telegram_id(
            telegram_id,
        )

        if not user:

            user = await self.user_repository.create(
                telegram_id=telegram_id,
            )

        existing_certificate = (
            await self.certificate_repository.get_by_cert_id(
                cert_id,
            )
        )

        if existing_certificate:

            raise Exception(
                "Certificate already exists",
            )

        file_name = await self.mikrotik.certs.create_cert(
            cert_id,
        )

        certificate = (
            await self.certificate_repository.create(
                cert_id=cert_id,
                user_id=user.id,
                file_path=f"./storage/certs/{file_name}",
            )
        )

        return certificate
