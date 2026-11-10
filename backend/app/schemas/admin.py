from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import ClientType, LeadStage, UserRole


class TeamMember(BaseModel):
    id: int
    full_name: str
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime
    clients: int
    open_leads: int
    upcoming_appointments: int


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    role: UserRole | None = None
    is_active: bool | None = None


class AssignmentRow(BaseModel):
    client_id: int
    client_name: str
    email: str | None
    phone: str | None
    client_type: ClientType
    preferred_city: str | None
    budget_max: float | None
    created_at: datetime
    from_website: bool
    lead_id: int | None
    lead_stage: LeadStage | None
    agent_id: int | None
    agent_name: str | None


class AssignRequest(BaseModel):
    agent_id: int


class AssignResult(AssignmentRow):
    moved_appointments: int
