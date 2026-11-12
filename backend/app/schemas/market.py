from datetime import date

from pydantic import BaseModel


class MarketRegion(BaseModel):
    region_id: int
    region_name: str
    state: str | None
    size_rank: int
    latest_month: date | None
    latest_inventory: int | None
    change_1y_pct: float | None


class MarketPoint(BaseModel):
    month: date
    inventory: int


class MarketStats(BaseModel):
    latest: int | None
    latest_month: date | None
    change_1y_pct: float | None          # vs the same month a year earlier
    change_vs_2019_pct: float | None     # vs the 2019 monthly average (before the pandemic)
    trend_3m: str | None                 # "rising", "falling" or "steady"
    peak: int | None
    peak_month: date | None
    low: int | None
    low_month: date | None
    summary: str                         # one plain-English sentence


class MarketSeries(BaseModel):
    region_id: int
    region_name: str
    state: str | None
    points: list[MarketPoint]
    stats: MarketStats


class MyArea(BaseModel):
    city: str
    clients: int
    region_id: int | None
    region_name: str | None
    match: str | None                    # "city", "chicago_area" or None (no market data)
    latest: int | None
    change_1y_pct: float | None
    trend_3m: str | None
