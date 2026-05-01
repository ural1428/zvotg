from datetime import datetime

from sqlalchemy import (
    ForeignKey,
    String,
    DateTime,
    Boolean,
    BigInteger,
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.database.base import Base


class Certificate(Base):

    __tablename__ = "certificates"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    cert_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        index=True,
    )

    file_path: Mapped[str] = mapped_column(
        String(500),
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="ACTIVE",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
    )

    user = relationship(
        "User",
        back_populates="certificates",
    )
