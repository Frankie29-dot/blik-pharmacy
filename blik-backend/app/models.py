import enum
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RefillMethod(str, enum.Enum):
    pickup = "pickup"
    delivery = "delivery"


class RefillStatus(str, enum.Enum):
    new = "new"
    preparing = "preparing"
    ready = "ready"
    collected = "collected"


class StaffRole(str, enum.Enum):
    pharmacist = "pharmacist"
    assistant = "assistant"


class Customer(Base):
    __tablename__ = "customers"
    # Phone numbers are not unique on their own: families often share one phone.
    # A customer is identified by phone + date of birth.
    __table_args__ = (UniqueConstraint("phone", "date_of_birth", name="uq_customers_phone_dob"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str | None] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(16))
    date_of_birth: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RefillRequest(Base):
    __tablename__ = "refill_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    prescription_number: Mapped[str] = mapped_column(String(40))
    method: Mapped[RefillMethod] = mapped_column(
        Enum(RefillMethod, name="refill_method", native_enum=False, create_constraint=True)
    )
    status: Mapped[RefillStatus] = mapped_column(
        Enum(RefillStatus, name="refill_status", native_enum=False, create_constraint=True),
        default=RefillStatus.new,
        server_default=RefillStatus.new.value,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    customer: Mapped[Customer] = relationship(lazy="joined")


class Staff(Base):
    __tablename__ = "staff"
    __table_args__ = (UniqueConstraint("email", name="uq_staff_email"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[StaffRole] = mapped_column(
        Enum(StaffRole, name="staff_role", native_enum=False, create_constraint=True)
    )
