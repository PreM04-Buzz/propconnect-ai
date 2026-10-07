from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import (
    AppointmentStatus,
    AppointmentType,
    ClientType,
    FinancingStatus,
    InteractionType,
    LeadStage,
    OfferStatus,
)


def _enum(e, length: int = 20):
    return Enum(e, native_enum=False, length=length)


class Client(TimestampMixin, Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    first_name: Mapped[str] = mapped_column(String(80))
    last_name: Mapped[str] = mapped_column(String(80))
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(30))
    client_type: Mapped[ClientType] = mapped_column(_enum(ClientType), default=ClientType.buyer)

    # Buyer preferences: inputs to property matching and lead scoring
    budget_min: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    budget_max: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    budget_confirmed: Mapped[bool] = mapped_column(default=False)
    preferred_city: Mapped[str | None] = mapped_column(String(100))
    preferred_state: Mapped[str | None] = mapped_column(String(50))
    preferred_zip: Mapped[str | None] = mapped_column(String(5))
    min_bedrooms: Mapped[int | None] = mapped_column(Integer)
    min_bathrooms: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    min_house_size_sqft: Mapped[int | None] = mapped_column(Integer)
    preferred_property_type: Mapped[str | None] = mapped_column(String(40))
    financing_status: Mapped[FinancingStatus] = mapped_column(
        _enum(FinancingStatus), default=FinancingStatus.unknown
    )
    purchase_timeline_months: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)

    leads: Mapped[list["Lead"]] = relationship(back_populates="client", cascade="all, delete-orphan", passive_deletes=True)


class Lead(TimestampMixin, Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    stage: Mapped[LeadStage] = mapped_column(_enum(LeadStage), default=LeadStage.new, index=True)
    source: Mapped[str | None] = mapped_column(String(60))  # website, referral, open house...
    score: Mapped[int | None] = mapped_column(Integer)  # 0-100, rule-based (Phase 4)
    priority: Mapped[str | None] = mapped_column(String(10))  # high / medium / low
    lost_reason: Mapped[str | None] = mapped_column(String(200))

    client: Mapped[Client] = relationship(back_populates="leads")
    history: Mapped[list["LeadStageHistory"]] = relationship(
        back_populates="lead", order_by="LeadStageHistory.id", cascade="all, delete-orphan", passive_deletes=True
    )


class LeadStageHistory(Base):
    """Every pipeline move is recorded so lead history is never lost."""

    __tablename__ = "lead_stage_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    from_stage: Mapped[LeadStage | None] = mapped_column(_enum(LeadStage))
    to_stage: Mapped[LeadStage] = mapped_column(_enum(LeadStage))
    changed_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lead: Mapped[Lead] = relationship(back_populates="history")


class PropertyInterest(TimestampMixin, Base):
    __tablename__ = "property_interests"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id", ondelete="CASCADE"), index=True)
    interest_level: Mapped[str] = mapped_column(String(10), default="medium")  # low/medium/high
    notes: Mapped[str | None] = mapped_column(Text)

    property: Mapped["Property"] = relationship("Property", lazy="joined")  # noqa: F821


class Interaction(TimestampMixin, Base):
    __tablename__ = "interactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    interaction_type: Mapped[InteractionType] = mapped_column(_enum(InteractionType))
    summary: Mapped[str] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class Appointment(TimestampMixin, Base):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(primary_key=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    property_id: Mapped[int | None] = mapped_column(ForeignKey("properties.id"), index=True)
    appointment_type: Mapped[AppointmentType] = mapped_column(_enum(AppointmentType))
    status: Mapped[AppointmentStatus] = mapped_column(
        _enum(AppointmentStatus), default=AppointmentStatus.scheduled
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
    outcome: Mapped[str | None] = mapped_column(Text)  # viewing feedback


class Offer(TimestampMixin, Base):
    __tablename__ = "offers"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True)
    lead_id: Mapped[int | None] = mapped_column(ForeignKey("leads.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    status: Mapped[OfferStatus] = mapped_column(_enum(OfferStatus), default=OfferStatus.draft)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
