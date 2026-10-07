from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession, ensure_owner
from app.api.routes.leads import get_lead
from app.core.config import get_settings
from app.models import AiSuggestion, Client, Interaction
from app.models.enums import InteractionType, SuggestionStatus
from app.schemas.ai import AiStatus, SuggestionDecision, SuggestionRead
from app.services.ai_assistant import generate_suggestion
from app.services.lead_scoring import refresh_client_leads

router = APIRouter(tags=["ai"])

ACTION_TO_INTERACTION = {
    "call": InteractionType.call, "email": InteractionType.email, "text": InteractionType.text,
    "send_listings": InteractionType.email,
}


@router.get("/ai/status", response_model=AiStatus)
def ai_status(_: CurrentUser) -> AiStatus:
    s = get_settings()
    return AiStatus(ai_enabled=bool(s.openai_api_key), model=s.openai_model if s.openai_api_key else None)


@router.post("/leads/{lead_id}/ai/next-step", response_model=SuggestionRead, status_code=status.HTTP_201_CREATED)
def next_step(lead_id: int, db: DbSession, user: CurrentUser) -> AiSuggestion:
    """Ask the AI Lead Assistant for the single most useful next step on this lead."""
    lead = get_lead(db, lead_id, user)
    return generate_suggestion(db, lead, user)


@router.get("/leads/{lead_id}/ai/suggestions", response_model=list[SuggestionRead])
def list_suggestions(lead_id: int, db: DbSession, user: CurrentUser) -> list[AiSuggestion]:
    lead = get_lead(db, lead_id, user)
    return list(db.scalars(select(AiSuggestion).where(AiSuggestion.lead_id == lead.id)
                           .order_by(AiSuggestion.id.desc()).limit(20)))


@router.post("/ai/suggestions/{suggestion_id}/decision", response_model=SuggestionRead)
def decide(suggestion_id: int, payload: SuggestionDecision, db: DbSession, user: CurrentUser) -> AiSuggestion:
    """The agent accepts or dismisses a suggestion. Accepting logs it on the client's timeline."""
    s = db.get(AiSuggestion, suggestion_id)
    if s is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Suggestion not found.")
    client = db.get(Client, s.client_id)
    ensure_owner(user, client.agent_id)
    if s.status != SuggestionStatus.suggested:
        raise HTTPException(status.HTTP_409_CONFLICT, "This suggestion has already been decided.")
    if payload.status == SuggestionStatus.suggested:
        raise HTTPException(422, "Choose accepted or dismissed.")
    if payload.draft_message:
        s.draft_message = payload.draft_message
    s.status = payload.status
    s.decided_at = datetime.now(timezone.utc)
    if payload.status == SuggestionStatus.accepted:
        db.add(Interaction(
            client_id=client.id, agent_id=user.id,
            interaction_type=ACTION_TO_INTERACTION.get(s.action_type, InteractionType.note),
            summary=f"AI next step accepted: {s.recommended_action}\n\nMessage: {s.draft_message}",
            occurred_at=datetime.now(timezone.utc),
        ))
        db.flush()
        refresh_client_leads(db, client)
    db.commit()
    db.refresh(s)
    return s
