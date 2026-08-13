import enum
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    DECIMAL,
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    event,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


def is_subdomain(domain: Optional[str]) -> bool:
    if not domain:
        return False
    return domain.count(".") > 1


class TransactionStatus(str, enum.Enum):
    PENDING = "jarayonda"
    SUCCESS = "muvaffaqiyatli"
    DECLINED = "bekor qilindi"
    TIMEOUT = "muddati o'tdi"


class ScanType(str, enum.Enum):
    DDOS = "Ddos attack"
    FULL_SCAN = "Full scan"


# --- MODELLAR ---

class Users(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(300))
    phone_number: Mapped[Optional[str]] = mapped_column(
        String(13), unique=True, nullable=True
    )
    telegram_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, unique=True, nullable=True
    )
    password: Mapped[str] = mapped_column(String(500))
    email: Mapped[str] = mapped_column(String(400), unique=True)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    webapplications: Mapped[List["WebApplications"]] = relationship(
        "WebApplications", back_populates="user", cascade="all, delete-orphan"
    )
    transactions: Mapped[List["TransactionHistory"]] = relationship(
        "TransactionHistory", back_populates="user", cascade="all, delete-orphan"
    )


class WebApplications(Base):
    __tablename__ = "web_applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )

    domain: Mapped[Optional[str]] = mapped_column(
        String(255), unique=True, nullable=True
    )
    title: Mapped[str] = mapped_column(String(200))
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_subdomain: Mapped[bool] = mapped_column(Boolean, default=False)
    slug: Mapped[str] = mapped_column(String(64), unique=True)

    verification_token: Mapped[str] = mapped_column(String(500), unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    user: Mapped["Users"] = relationship("Users", back_populates="webapplications")
    transactions: Mapped[List["TransactionHistory"]] = relationship(
        "TransactionHistory", back_populates="webapp", cascade="all, delete-orphan"
    )
    scans: Mapped[List["ScanHistory"]] = relationship(
        "ScanHistory", back_populates="webapp", cascade="all, delete-orphan"
    )

    def verif_token(self) -> dict:
        return {"verification_token": self.verification_token}

    def __repr__(self) -> str:
        return f"<WebApplications(domain='{self.domain}')>"


class TransactionHistory(Base):
    __tablename__ = "transaction_histories"

    id: Mapped[int] = mapped_column(primary_key=True)

    webapp_id: Mapped[int] = mapped_column(
        ForeignKey("web_applications.id", ondelete="CASCADE")
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )

    payment_id: Mapped[str] = mapped_column(String(300), unique=True)
    amount: Mapped[float] = mapped_column(DECIMAL(10, 2), default=20000.00)
    status: Mapped[TransactionStatus] = mapped_column(
        Enum(TransactionStatus), default=TransactionStatus.PENDING
    )
    payment_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    webapp: Mapped["WebApplications"] = relationship("WebApplications", back_populates="transactions")
    user: Mapped["Users"] = relationship("Users", back_populates="transactions")

    def __repr__(self) -> str:
        return f"<TransactionHistory(payment_id='{self.payment_id}', amount={self.amount})>"


class ScanHistory(Base):
    __tablename__ = "scan_histories"

    id: Mapped[int] = mapped_column(primary_key=True)

    webapp_id: Mapped[int] = mapped_column(
        ForeignKey("web_applications.id", ondelete="CASCADE")
    )
    scanned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    result_summary: Mapped[str] = mapped_column(Text)
    scan_type: Mapped[ScanType] = mapped_column(Enum(ScanType))

    task_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), unique=True, index=True, nullable=True
    )

    # Relationship
    webapp: Mapped["WebApplications"] = relationship("WebApplications", back_populates="scans")

    def __repr__(self) -> str:
        return f"<ScanHistory(webapp_id={self.webapp_id}, scan_type='{self.scan_type}')>"


# --- EVENT LISTENERS ---

@event.listens_for(WebApplications, "before_insert")
def generate_fields_before_insert(mapper, connection, target):
    target.is_subdomain = is_subdomain(target.domain)

    # UUID4 unikal bo'lgani uchun ortiqcha while DB-zaprosisiz to'g'ridan-to'g'ri biriktirish tezroq va xavfsizroq
    if not target.verification_token:
        target.verification_token = f"devguard-verification:{uuid.uuid4().hex}"

    if not target.slug:
        target.slug = f"app-{uuid.uuid4().hex[:12]}"


@event.listens_for(WebApplications, "before_update")
def check_subdomain_before_update(mapper, connection, target):
    target.is_subdomain = is_subdomain(target.domain)


@event.listens_for(TransactionHistory, "before_insert")
def generate_payment_id(mapper, connection, target):
    if not target.payment_id:
        target.payment_id = f"devguard_payment_{uuid.uuid4().hex}"