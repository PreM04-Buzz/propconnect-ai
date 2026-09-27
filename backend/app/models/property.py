from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Enum, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.enums import PropertyStatus


class Property(TimestampMixin, Base):
    """A listing. Loaded from the cleaned USA Real Estate dataset in Phase 2."""

    __tablename__ = "properties"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_ref: Mapped[str | None] = mapped_column(String(64), index=True)
    status: Mapped[PropertyStatus] = mapped_column(
        Enum(PropertyStatus, native_enum=False, length=20), index=True
    )
    price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), index=True)
    bedrooms: Mapped[int | None] = mapped_column(Integer)
    bathrooms: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    house_size_sqft: Mapped[int | None] = mapped_column(Integer)
    acre_lot: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))
    # The source dataset anonymizes street, so demo addresses are generated.
    street_address: Mapped[str | None] = mapped_column(String(200))
    city: Mapped[str] = mapped_column(String(100), index=True)
    state: Mapped[str] = mapped_column(String(50), index=True)
    zip_code: Mapped[str] = mapped_column(String(5), index=True)  # string keeps leading zeros
    # Not in the source dataset; filled manually for demo records.
    property_type: Mapped[str | None] = mapped_column(String(40))
    prev_sold_date: Mapped[date | None] = mapped_column(Date)
