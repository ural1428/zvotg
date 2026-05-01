from sqlalchemy import (
    select,
)

from app.repositories.base import (
    BaseRepository,
)

from app.database.models.certificate import (
    Certificate,
)


class CertificateRepository(
    BaseRepository
):

    async def create(
        self,
        user_id: int,
        cert_id: int,
        file_path: str,
        status: str = "ACTIVE",
    ):

        cert = Certificate(
            user_id=user_id,
            cert_id=cert_id,
            file_path=file_path,
            status=status,
        )

        self.session.add(cert)

        await self.session.commit()

        await self.session.refresh(cert)

        return cert

    async def get_by_cert_id(
        self,
        cert_id: int,
    ):

        query = select(Certificate).where(
            Certificate.cert_id == cert_id
        )

        result = await self.session.execute(
            query
        )

        return result.scalar_one_or_none()

    async def get_user_certificates(
        self,
        user_id: int,
    ):

        query = select(Certificate).where(
            Certificate.user_id == user_id
        )

        result = await self.session.execute(
            query
        )

        return result.scalars().all()

    async def deactivate(
        self,
        cert_id: int,
    ):

        cert = await self.get_by_cert_id(
            cert_id
        )

        if not cert:
            return None

        cert.is_active = False
        cert.status = "DISABLED"

        await self.session.commit()

        return cert
