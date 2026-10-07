from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import LeadStage
from app.schemas.client import ClientRead
from app.schemas.common import ORMModel


class LeadCreate(BaseModel):
    client_id: int
    source: str | None = Field(default=None, max_length=60)


class LeadUpdate(BaseModel):
    source: str | None = Field(default=None, max_length=60)


class LeadMove(BaseModel):
    to_stage: LeadStage
    lost_reason: str | None = Field(default=None, max_length=200)


class LeadCard(BaseModel):
    id: int
    stage: LeadStage
    source: str | None
    score: int | None
    priority: str | None
    client_id: int
    client_name: str
    client_type: str
    budget_max: float | None
    preferred_city: str | None
    last_contact_at: datetime | None
    updated_at: datetime


class StageCount(BaseModel):
    stage: LeadStage
    count: int


class StageHistoryRead(ORMModel):
    id: int
    from_stage: LeadStage | None
    to_stage: LeadStage
    changed_by_id: int
    changed_at: datetime


class ScoreItemRead(BaseModel):
    factor: str
    points: int
    max_points: int
    reason: str


class LeadDetail(ORMModel):
    id: int
    stage: LeadStage
    source: str | None
    score: int | None
    priority: str | None
    lost_reason: str | None
    agent_id: int
    created_at: datetime
    updated_at: datetime
    client: ClientRead
    history: list[StageHistoryRead]
    score_breakdown: list[ScoreItemRead]
