from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import LeadStage, OfferStatus


class OfferCreate(BaseModel):
    client_id: int
    property_id: int
    amount: float = Field(gt=0)
    notes: str | None = Field(default=None, max_length=2000)
    submit: bool = Field(default=True, description="Submit now, or keep as a draft")


class OfferStatusChange(BaseModel):
    status: OfferStatus
    amount: float | None = Field(default=None, gt=0, description="A revised amount when resubmitting")
    counter_amount: float | None = Field(default=None, gt=0, description="Required when the seller counters")
    notes: str | None = Field(default=None, max_length=2000)


class OfferRead(BaseModel):
    id: int
    client_id: int
    client_name: str
    property_id: int
    property_address: str
    list_price: float | None
    lead_id: int | None
    lead_stage: LeadStage | None
    amount: float
    counter_amount: float | None
    status: OfferStatus
    submitted_at: datetime | None
    decided_at: datetime | None
    notes: str | None
    created_at: datetime
