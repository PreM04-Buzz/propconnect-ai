from datetime import date

from pydantic import BaseModel, Field

from app.models.enums import PropertyStatus
from app.schemas.common import ORMModel


class PropertyBase(BaseModel):
    status: PropertyStatus = PropertyStatus.for_sale
    price: float | None = Field(default=None, ge=0)
    bedrooms: int | None = Field(default=None, ge=0, le=50)
    bathrooms: float | None = Field(default=None, ge=0, le=50)
    house_size_sqft: int | None = Field(default=None, ge=0)
    acre_lot: float | None = Field(default=None, ge=0)
    street_address: str | None = Field(default=None, max_length=200)
    city: str = Field(min_length=1, max_length=100)
    state: str = Field(min_length=1, max_length=50)
    zip_code: str = Field(pattern=r"^\d{5}$")
    property_type: str | None = Field(default=None, max_length=40)


class PropertyCreate(PropertyBase):
    pass


class PropertyUpdate(BaseModel):
    status: PropertyStatus | None = None
    price: float | None = Field(default=None, ge=0)
    bedrooms: int | None = Field(default=None, ge=0, le=50)
    bathrooms: float | None = Field(default=None, ge=0, le=50)
    house_size_sqft: int | None = Field(default=None, ge=0)
    street_address: str | None = Field(default=None, max_length=200)
    property_type: str | None = Field(default=None, max_length=40)


class PropertyRead(ORMModel, PropertyBase):
    id: int
    prev_sold_date: date | None = None


class PropertyPage(BaseModel):
    items: list[PropertyRead]
    total: int
    page: int
    page_size: int


class CityCount(BaseModel):
    city: str
    count: int


class PropertyMatch(BaseModel):
    property: PropertyRead
    score: int
    reasons: list[str]
