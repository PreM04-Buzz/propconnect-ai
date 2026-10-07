from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import SuggestionSource, SuggestionStatus
from app.schemas.common import ORMModel

ACTION_TYPES = ("call", "email", "text", "schedule_viewing", "send_listings", "follow_up_later", "update_profile")


class AiOutput(BaseModel):
    """The exact shape the model must return. Anything else is rejected."""

    intent_level: str = Field(pattern="^(high|medium|low)$")
    summary: str = Field(min_length=1, max_length=800)
    recommended_action: str = Field(min_length=1, max_length=500)
    action_type: str = Field(pattern="^(" + "|".join(ACTION_TYPES) + ")$")
    reasoning: str = Field(min_length=1, max_length=800)
    draft_message: str = Field(min_length=1, max_length=1500)


class SuggestionRead(ORMModel):
    id: int
    lead_id: int
    client_id: int
    source: SuggestionSource
    model: str | None
    intent_level: str
    summary: str
    recommended_action: str
    action_type: str
    reasoning: str
    draft_message: str
    status: SuggestionStatus
    created_at: datetime
    decided_at: datetime | None


class SuggestionDecision(BaseModel):
    status: SuggestionStatus = Field(description="accepted or dismissed")
    draft_message: str | None = Field(default=None, max_length=1500, description="The agent's edited draft, if changed")


class AiStatus(BaseModel):
    ai_enabled: bool
    model: str | None
