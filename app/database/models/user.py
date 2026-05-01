from datetime import datetime

from sqlalchemy import (
    BigInteger,
    String,
    DateTime,
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.database.base import Base


class User(Base):

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        index=True,
    )

    username: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    certificates = relationship(
        "Certificate",
        back_populates="user",
    )
