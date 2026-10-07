from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.models.enums import ClientType, FinancingStatus, InteractionType, LeadStage
from app.schemas.common import ORMModel
from app.schemas.property import PropertyRead


class ClientFields(BaseModel):
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=30)
    client_type: ClientType = ClientType.buyer
    budget_min: float | None = Field(default=None, ge=0)
    budget_max: float | None = Field(default=None, ge=0)
    budget_confirmed: bool = False
    preferred_city: str | None = Field(default=None, max_length=100)
    preferred_state: str | None = Field(default="Illinois", max_length=50)
    preferred_zip: str | None = Field(default=None, pattern=r"^\d{5}$")
    min_bedrooms: int | None = Field(default=None, ge=0, le=20)
    min_bathrooms: float | None = Field(default=None, ge=0, le=20)
    min_house_size_sqft: int | None = Field(default=None, ge=0)
    preferred_property_type: str | None = Field(default=None, max_length=40)
    financing_status: FinancingStatus = FinancingStatus.unknown
    purchase_timeline_months: int | None = Field(default=None, ge=0, le=120)
    notes: str | None = None

    @model_validator(mode="after")
    def budget_order(self):
        if self.budget_min is not None and self.budget_max is not None and self.budget_min > self.budget_max:
            raise ValueError("Minimum budget can't be higher than maximum budget.")
        return self


class ClientCreate(ClientFields):
    create_lead: bool = True
    lead_source: str | None = Field(default=None, max_length=60)
    agent_id: int | None = None  # admins may assign a client to an agent


class ClientUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=80)
    last_name: str | None = Field(default=None, min_length=1, max_length=80)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=30)
    client_type: ClientType | None = None
    budget_min: float | None = Field(default=None, ge=0)
    budget_max: float | None = Field(default=None, ge=0)
    budget_confirmed: bool | None = None
    preferred_city: str | None = Field(default=None, max_length=100)
    preferred_state: str | None = Field(default=None, max_length=50)
    preferred_zip: str | None = Field(default=None, pattern=r"^\d{5}$")
    min_bedrooms: int | None = Field(default=None, ge=0, le=20)
    min_bathrooms: float | None = Field(default=None, ge=0, le=20)
    min_house_size_sqft: int | None = Field(default=None, ge=0)
    preferred_property_type: str | None = Field(default=None, max_length=40)
    financing_status: FinancingStatus | None = None
    purchase_timeline_months: int | None = Field(default=None, ge=0, le=120)
    notes: str | None = None


class ClientRead(ORMModel, ClientFields):
    id: int
    agent_id: int
    created_at: datetime
    updated_at: datetime


class ClientListItem(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str | None
    phone: str | None
    client_type: ClientType
    budget_max: float | None
    preferred_city: str | None
    financing_status: FinancingStatus
    lead_id: int | None
    lead_stage: LeadStage | None
    lead_priority: str | None
    updated_at: datetime


class InteractionCreate(BaseModel):
    interaction_type: InteractionType
    summary: str = Field(min_length=1, max_length=4000)
    occurred_at: datetime | None = None


class InteractionRead(ORMModel):
    id: int
    client_id: int
    agent_id: int
    interaction_type: InteractionType
    summary: str
    occurred_at: datetime


class InterestCreate(BaseModel):
    property_id: int
    interest_level: str = Field(default="medium", pattern="^(low|medium|high)$")
    notes: str | None = None


class InterestRead(ORMModel):
    id: int
    property_id: int
    interest_level: str
    notes: str | None
    property: PropertyRead


class LeadBrief(ORMModel):
    id: int
    stage: LeadStage
    source: str | None
    score: int | None
    priority: str | None
    updated_at: datetime


class ClientDetail(ClientRead):
    leads: list[LeadBrief]
    interactions: list[InteractionRead]
    interests: list[InterestRead]
