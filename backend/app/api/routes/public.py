"""Endpoints anyone can call, without signing in. Kept deliberately small."""
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import func, select

from app.api.deps import DbSession
from app.core import rate_limit
from app.models import Client, Lead, LeadStageHistory
from app.models.enums import LeadStage
from app.schemas.intake import IntakeCreate, IntakeReply
from app.services.lead_scoring import refresh_client_leads

router = APIRouter(prefix="/public", tags=["public"])

THANKS = ("Thank you! We’ve received your details, and an agent will get in touch soon "
          "using the email or phone number you gave us.")
PER_HOUR = 5


def _client_ip(request: Request) -> str:
    # Behind Render's proxy the real address is the first one in X-Forwarded-For.
    forwarded = request.headers.get("x-forwarded-for", "")
    return forwarded.split(",")[0].strip() or (request.client.host if request.client else "unknown")


@router.post("/intake", response_model=IntakeReply, status_code=status.HTTP_202_ACCEPTED)
def submit_intake(payload: IntakeCreate, request: Request, db: DbSession) -> IntakeReply:
    """A client describes what they’re looking for. The request waits, unassigned, until the
    broker gives it to an agent. The reply is the same whether or not we already know this
    email address, so the form can’t be used to find out who our clients are."""
    if not rate_limit.allow(f"intake:{_client_ip(request)}", PER_HOUR):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            "Thanks, we already have your request. Please try again in an hour if something changed.")
    if payload.website:  # honeypot filled in: almost certainly a bot
        return IntakeReply(message=THANKS)

    now = datetime.now(timezone.utc)
    email = payload.email.lower()
    existing = db.scalar(select(Client).where(func.lower(Client.email) == email).order_by(Client.id))
    stamp = f"[Website form, {now.date().isoformat()}]"
    if existing:
        # Don't overwrite what an agent has recorded; add the new request to the notes instead.
        wishes = ", ".join(x for x in [
            payload.client_type.value, payload.preferred_city or "",
            f"up to ${payload.budget_max:,.0f}" if payload.budget_max else "",
            f"{payload.min_bedrooms}+ beds" if payload.min_bedrooms else "",
        ] if x)
        extra = f"{stamp} Sent the form again: {wishes}. {payload.notes or ''}".strip()
        existing.notes = f"{existing.notes}\n{extra}" if existing.notes else extra
        db.commit()
        return IntakeReply(message=THANKS)

    client = Client(
        agent_id=None, first_name=payload.first_name.strip(), last_name=payload.last_name.strip(), email=email,
        phone=(payload.phone or "").strip() or None, client_type=payload.client_type,
        preferred_city=(payload.preferred_city or "").strip() or None, preferred_state=payload.preferred_state,
        budget_min=payload.budget_min, budget_max=payload.budget_max, budget_confirmed=False,
        min_bedrooms=payload.min_bedrooms, min_bathrooms=payload.min_bathrooms,
        financing_status=payload.financing_status, purchase_timeline_months=payload.purchase_timeline_months,
        notes=f"{stamp} {payload.notes.strip()}" if payload.notes and payload.notes.strip() else None,
        consent_at=now,
    )
    db.add(client)
    db.flush()
    lead = Lead(client_id=client.id, agent_id=None, stage=LeadStage.new, source="Website form")
    db.add(lead)
    db.flush()
    db.add(LeadStageHistory(lead_id=lead.id, from_stage=None, to_stage=LeadStage.new, changed_by_id=None))
    refresh_client_leads(db, client)
    db.commit()
    return IntakeReply(message=THANKS)
