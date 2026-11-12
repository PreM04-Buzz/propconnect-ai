"""Market trends from Zillow's monthly for-sale inventory (one row per metro per month)."""
from collections import defaultdict
from datetime import date
from statistics import mean

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import MarketInventory, Property

# ZIP codes starting 600-608 are the Chicago area, so a client asking for a suburb such as
# Naperville or Evanston is shown the Chicago metro rather than nothing.
CHICAGO_ZIP_PREFIXES = tuple(str(n) for n in range(600, 609))
STATES = {"illinois": "IL", "indiana": "IN", "wisconsin": "WI", "iowa": "IA", "missouri": "MO", "michigan": "MI"}


def series(db: Session, region_id: int) -> list[tuple[date, int]]:
    rows = db.execute(select(MarketInventory.month, MarketInventory.inventory)
                      .where(MarketInventory.region_id == region_id, MarketInventory.inventory.is_not(None))
                      .order_by(MarketInventory.month)).all()
    return [(m, int(v)) for m, v in rows]


def _pct(new: float, old: float | None) -> float | None:
    return round((new - old) / old * 100, 1) if old else None


def stats(points: list[tuple[date, int]], name: str = "This area") -> dict:
    if not points:
        return {"latest": None, "latest_month": None, "change_1y_pct": None, "change_vs_2019_pct": None,
                "trend_3m": None, "peak": None, "peak_month": None, "low": None, "low_month": None,
                "summary": f"No inventory data for {name}."}
    last_month, latest = points[-1]
    year_ago = next((v for m, v in points if (m.year, m.month) == (last_month.year - 1, last_month.month)), None)
    in_2019 = [v for m, v in points if m.year == 2019]
    base_2019 = mean(in_2019) if in_2019 else None
    three_back = points[-4][1] if len(points) >= 4 else None
    d3 = _pct(latest, three_back)
    trend = None if d3 is None else "rising" if d3 > 2 else "falling" if d3 < -2 else "steady"
    peak_m, peak = max(points, key=lambda p: p[1])
    low_m, low = min(points, key=lambda p: p[1])
    c1, c19 = _pct(latest, year_ago), _pct(latest, base_2019)

    # A plain sentence an agent can repeat to a client. More homes for sale: buyers have more choice.
    parts = [f"{name} had {latest:,} homes for sale in {last_month:%B %Y}"]
    if c1 is not None:
        parts.append(f"{'up' if c1 >= 0 else 'down'} {abs(c1):.0f}% on a year earlier")
    sentence = ", ".join(parts) + "."
    if c19 is not None:
        if c19 <= -15:
            sentence += f" That’s well below the 2019 level ({c19:+.0f}%): buyers have far fewer homes to choose from, so good ones move quickly."
        elif c19 < -3:
            sentence += f" That’s a little below the 2019 level ({c19:+.0f}%): buyers have slightly less choice than before the pandemic."
        elif c19 <= 3:
            sentence += f" That’s close to the 2019 level ({c19:+.0f}%): buyers have about as much choice as before the pandemic."
        else:
            sentence += f" That’s above the 2019 level ({c19:+.0f}%): buyers have more choice and more room to negotiate."
    return {"latest": latest, "latest_month": last_month, "change_1y_pct": c1, "change_vs_2019_pct": c19,
            "trend_3m": trend, "peak": peak, "peak_month": peak_m, "low": low, "low_month": low_m,
            "summary": sentence}


def latest_by_region(db: Session, region_ids: list[int]) -> dict[int, tuple[date, int, float | None]]:
    """Latest month, value and one-year change for several regions in two queries."""
    if not region_ids:
        return {}
    rows = db.execute(select(MarketInventory.region_id, MarketInventory.month, MarketInventory.inventory)
                      .where(MarketInventory.region_id.in_(region_ids), MarketInventory.inventory.is_not(None))).all()
    per: dict[int, dict[tuple[int, int], tuple[date, int]]] = defaultdict(dict)
    for rid, m, v in rows:
        per[rid][(m.year, m.month)] = (m, int(v))
    out = {}
    for rid, months in per.items():
        y, mo = max(months)
        when, latest = months[(y, mo)]
        before = months.get((y - 1, mo))
        out[rid] = (when, latest, _pct(latest, before[1] if before else None))
    return out


def match_city(db: Session, city: str, state: str | None) -> tuple[int, str, str] | None:
    """The metro for a client's preferred city: (region_id, region_name, how it matched), or None."""
    abbr = STATES.get((state or "").strip().lower(), (state or "").strip().upper()[:2] or None)
    q = select(MarketInventory.region_id, MarketInventory.region_name).where(
        func.lower(MarketInventory.region_name).like(f"{city.strip().lower()},%"))
    if abbr:
        q = q.where(MarketInventory.state_name == abbr)
    hit = db.execute(q.limit(1)).first()
    if hit:
        return hit[0], hit[1], "city"
    zips = db.scalars(select(Property.zip_code).where(func.lower(Property.city) == city.strip().lower()).limit(25)).all()
    if zips and all(z.startswith(CHICAGO_ZIP_PREFIXES) for z in zips):
        chicago = db.execute(select(MarketInventory.region_id, MarketInventory.region_name)
                             .where(MarketInventory.region_name == "Chicago, IL").limit(1)).first()
        if chicago:
            return chicago[0], chicago[1], "chicago_area"
    return None
