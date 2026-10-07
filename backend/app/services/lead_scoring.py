"""Rule-based lead score (0-100), as specified in the design document.

Scores are deterministic and explainable: every point comes with a reason the
agent can read. The AI never sets the score.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Appointment, Client, Interaction, Lead, PropertyInterest
from app.models.enums import AppointmentStatus, AppointmentType, FinancingStatus, LeadStage


@dataclass
class ScoreItem:
    factor: str
    points: int
    max_points: int
    reason: str


@dataclass
class LeadScore:
    score: int
    priority: str
    items: list[ScoreItem] = field(default_factory=list)


def priority_for(score: int) -> str:
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def compute_score(db: Session, client: Client, now: datetime | None = None) -> LeadScore:
    now = now or datetime.now(timezone.utc)
    items: list[ScoreItem] = []

    # Financing readiness (20)
    fin = client.financing_status
    if fin in (FinancingStatus.pre_approved, FinancingStatus.cash):
        items.append(ScoreItem("Financing", 20, 20, f"Financing is {fin.value.replace('_', '-')}"))
    elif fin == FinancingStatus.pre_qualified:
        items.append(ScoreItem("Financing", 10, 20, "Pre-qualified, not yet pre-approved"))
    else:
        items.append(ScoreItem("Financing", 0, 20, "Financing not confirmed"))

    # Purchase timeline (20)
    t = client.purchase_timeline_months
    if t is not None and t <= 3:
        items.append(ScoreItem("Timeline", 20, 20, f"Wants to buy within {t} month(s)"))
    elif t is not None and t <= 6:
        items.append(ScoreItem("Timeline", 10, 20, f"Wants to buy within {t} months"))
    else:
        items.append(ScoreItem("Timeline", 0, 20, "No near-term purchase timeline"))

    # Viewing activity (20)
    viewings = db.scalar(
        select(func.count(Appointment.id)).where(
            Appointment.client_id == client.id,
            Appointment.appointment_type == AppointmentType.viewing,
            Appointment.status.in_([AppointmentStatus.completed, AppointmentStatus.scheduled]),
        )
    ) or 0
    pts = 20 if viewings >= 2 else 10 if viewings == 1 else 0
    items.append(ScoreItem("Viewings", pts, 20, f"{viewings} viewing(s) scheduled or completed"))

    # Confirmed budget (15)
    if client.budget_confirmed and client.budget_max:
        items.append(ScoreItem("Budget", 15, 15, f"Budget confirmed up to ${client.budget_max:,.0f}"))
    else:
        items.append(ScoreItem("Budget", 0, 15, "Budget not confirmed"))

    # Recent communication (15)
    last = _aware(db.scalar(select(func.max(Interaction.occurred_at)).where(Interaction.client_id == client.id)))
    if last and now - last <= timedelta(days=7):
        items.append(ScoreItem("Recent contact", 15, 15, "Contacted in the last 7 days"))
    elif last and now - last <= timedelta(days=30):
        items.append(ScoreItem("Recent contact", 8, 15, "Contacted in the last 30 days"))
    else:
        items.append(ScoreItem("Recent contact", 0, 15, "No contact in the last 30 days"))

    # Specific property interest (10)
    interests = db.scalar(
        select(func.count(PropertyInterest.id)).where(
            PropertyInterest.client_id == client.id, PropertyInterest.interest_level.in_(["medium", "high"])
        )
    ) or 0
    pts = 10 if interests else 0
    items.append(ScoreItem("Property interest", pts, 10, f"Interested in {interests} specific propert{'y' if interests == 1 else 'ies'}"))

    score = sum(i.points for i in items)
    return LeadScore(score=score, priority=priority_for(score), items=items)


def refresh_client_leads(db: Session, client: Client) -> None:
    """Recompute and store the score on every open lead of a client."""
    result = compute_score(db, client)
    for lead in db.scalars(select(Lead).where(Lead.client_id == client.id)):
        if lead.stage in (LeadStage.won, LeadStage.lost):
            continue
        lead.score = result.score
        lead.priority = result.priority
