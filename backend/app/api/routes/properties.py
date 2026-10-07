from typing import Literal

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, or_, select

from app.api.deps import AdminUser, CurrentUser, DbSession
from app.models import Property
from app.models.enums import PropertyStatus
from app.schemas.property import CityCount, PropertyCreate, PropertyPage, PropertyRead, PropertyUpdate

router = APIRouter(prefix="/properties", tags=["properties"])

SORTS = {
    "price_asc": Property.price.asc(),
    "price_desc": Property.price.desc(),
    "newest": Property.id.desc(),
    "size_desc": Property.house_size_sqft.desc(),
}


@router.get("", response_model=PropertyPage)
def list_properties(
    db: DbSession, _: CurrentUser,
    q: str | None = Query(default=None, description="Search address, city or ZIP"),
    city: str | None = None,
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    min_beds: int | None = Query(default=None, ge=0),
    min_baths: float | None = Query(default=None, ge=0),
    status_: PropertyStatus | None = Query(default=PropertyStatus.for_sale, alias="status"),
    sort: Literal["price_asc", "price_desc", "newest", "size_desc"] = "price_asc",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=24, ge=1, le=100),
) -> PropertyPage:
    query = select(Property)
    if q:
        like = f"%{q.strip()}%"
        query = query.where(or_(Property.street_address.ilike(like), Property.city.ilike(like),
                                Property.zip_code.ilike(like)))
    if city:
        query = query.where(Property.city.ilike(city))
    if min_price is not None:
        query = query.where(Property.price >= min_price)
    if max_price is not None:
        query = query.where(Property.price <= max_price)
    if min_beds is not None:
        query = query.where(Property.bedrooms >= min_beds)
    if min_baths is not None:
        query = query.where(Property.bathrooms >= min_baths)
    if status_ is not None:
        query = query.where(Property.status == status_)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(query.order_by(SORTS[sort], Property.id).offset((page - 1) * page_size).limit(page_size))
    return PropertyPage(items=list(items), total=total, page=page, page_size=page_size)


@router.get("/cities", response_model=list[CityCount])
def list_cities(db: DbSession, _: CurrentUser, limit: int = Query(default=60, ge=1, le=500)) -> list[CityCount]:
    rows = db.execute(select(Property.city, func.count(Property.id).label("n"))
                      .where(Property.status == PropertyStatus.for_sale)
                      .group_by(Property.city).order_by(func.count(Property.id).desc(), Property.city).limit(limit))
    return [CityCount(city=c, count=n) for c, n in rows]


@router.get("/{property_id}", response_model=PropertyRead)
def read_property(property_id: int, db: DbSession, _: CurrentUser) -> Property:
    item = db.get(Property, property_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Property not found.")
    return item


@router.post("", response_model=PropertyRead, status_code=status.HTTP_201_CREATED)
def create_property(payload: PropertyCreate, db: DbSession, _: CurrentUser) -> Property:
    item = Property(**payload.model_dump(), source_ref="manual")
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{property_id}", response_model=PropertyRead)
def update_property(property_id: int, payload: PropertyUpdate, db: DbSession, _: CurrentUser) -> Property:
    item = read_property(property_id, db, _)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_property(property_id: int, db: DbSession, _: AdminUser) -> None:
    item = db.get(Property, property_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Property not found.")
    db.delete(item)
    db.commit()
