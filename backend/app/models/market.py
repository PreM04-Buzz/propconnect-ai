from datetime import date

from sqlalchemy import Date, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MarketInventory(Base):
    """Zillow metro for-sale inventory, reshaped to one row per region per month."""

    __tablename__ = "market_inventory"
    __table_args__ = (UniqueConstraint("region_id", "month", name="uq_region_month"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    region_id: Mapped[int] = mapped_column(Integer, index=True)
    region_name: Mapped[str] = mapped_column(String(120), index=True)
    region_type: Mapped[str] = mapped_column(String(20))
    state_name: Mapped[str | None] = mapped_column(String(10))
    size_rank: Mapped[int] = mapped_column(Integer)
    month: Mapped[date] = mapped_column(Date, index=True)
    inventory: Mapped[int | None] = mapped_column(Integer)
