from app.repositories.certificates import (
    CertificateRepository,
)

from app.integrations.mikrotik.manager import (
    MikroTikManager,
)


class CertificateService:

    def __init__(
        self,
        cert_repo: CertificateRepository,
        mikrotik: MikroTikManager,
    ):

        self.cert_repo = cert_repo
        self.mikrotik = mikrotik

    async def create_certificate(
        self,
        user_id: int,
        cert_id: int,
    ):

        file_name = await self.mikrotik.certs.create_cert(
            cert_id=cert_id,
        )

        cert = await self.cert_repo.create(
            user_id=user_id,
            cert_id=cert_id,
            file_path=f"./storage/certs/{file_name}",
            status="ACTIVE",
        )

        return cert

    async def disable_certificate(
        self,
        cert_id: int,
    ):

        await self.mikrotik.certs.disable_cert(
            cert_id=cert_id,
        )

        return await self.cert_repo.deactivate(
            cert_id=cert_id,
        )
