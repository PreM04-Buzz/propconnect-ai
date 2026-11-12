"""Market trends: Zillow's monthly count of homes for sale, by metro area."""
from collections import Counter

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession, is_admin
from app.models import Client, MarketInventory
from app.schemas.market import MarketPoint, MarketRegion, MarketSeries, MarketStats, MyArea
from app.services import market

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/regions", response_model=list[MarketRegion])
def regions(db: DbSession, _: CurrentUser, q: str = Query(default="", max_length=60)) -> list[MarketRegion]:
    """Find metro areas by name. With no search, the United States and the Illinois metros."""
    base = select(MarketInventory.region_id, MarketInventory.region_name, MarketInventory.state_name,
                  MarketInventory.size_rank).distinct()
    if q.strip():
        base = base.where(func.lower(MarketInventory.region_name).like(f"%{q.strip().lower()}%"))
    else:
        base = base.where((MarketInventory.state_name == "IL") | (MarketInventory.region_type == "country"))
    found = db.execute(base.order_by(MarketInventory.size_rank).limit(25)).all()
    latest = market.latest_by_region(db, [r[0] for r in found])
    return [MarketRegion(region_id=rid, region_name=name, state=st, size_rank=rank,
                         latest_month=latest.get(rid, (None,))[0], latest_inventory=latest.get(rid, (None, None))[1],
                         change_1y_pct=latest.get(rid, (None, None, None))[2])
            for rid, name, st, rank in found]


@router.get("/trends", response_model=list[MarketSeries])
def trends(db: DbSession, _: CurrentUser, region_id: list[int] = Query(min_length=1, max_length=3)) -> list[MarketSeries]:
    """Monthly homes for sale for up to three areas, with plain-English statistics."""
    out = []
    for rid in dict.fromkeys(region_id):
        info = db.execute(select(MarketInventory.region_name, MarketInventory.state_name)
                          .where(MarketInventory.region_id == rid).limit(1)).first()
        if info is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"No market data for area {rid}.")
        pts = market.series(db, rid)
        out.append(MarketSeries(region_id=rid, region_name=info[0], state=info[1],
                                points=[MarketPoint(month=m, inventory=v) for m, v in pts],
                                stats=MarketStats(**market.stats(pts, info[0]))))
    return out


@router.get("/my-areas", response_model=list[MyArea])
def my_areas(db: DbSession, user: CurrentUser) -> list[MyArea]:
    """The market where your clients want to live (a broker sees every client's area)."""
    q = select(Client.preferred_city, Client.preferred_state).where(Client.preferred_city.is_not(None))
    if not is_admin(user):
        q = q.where(Client.agent_id == user.id)
    counts = Counter((c.strip(), s) for c, s in db.execute(q).all() if c and c.strip())
    matched = {key: market.match_city(db, *key) for key in counts}
    latest = market.latest_by_region(db, sorted({m[0] for m in matched.values() if m}))
    trends = {rid: market.stats(market.series(db, rid))["trend_3m"] for rid in latest}
    areas = []
    for (city, state), n in counts.most_common(12):
        m = matched[(city, state)]
        trend = trends.get(m[0]) if m else None
        lt = latest.get(m[0]) if m else None
        areas.append(MyArea(city=city, clients=n, region_id=m[0] if m else None, region_name=m[1] if m else None,
                            match=m[2] if m else None, latest=lt[1] if lt else None,
                            change_1y_pct=lt[2] if lt else None, trend_3m=trend))
    return areas
