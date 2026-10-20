"""Moving a lead between stages, used by the board and by automatic moves (offers)."""
from sqlalchemy.orm import Session

from app.models import Lead, LeadStageHistory, User
from app.models.enums import LeadStage

ORDER = [LeadStage.new, LeadStage.contacted, LeadStage.qualified, LeadStage.proposal,
         LeadStage.negotiation, LeadStage.won]


def move(db: Session, lead: Lead, to_stage: LeadStage, user: User, lost_reason: str | None = None) -> bool:
    """Record the move in the stage history. Returns False if the lead was already there."""
    if lead.stage == to_stage:
        return False
    db.add(LeadStageHistory(lead_id=lead.id, from_stage=lead.stage, to_stage=to_stage, changed_by_id=user.id))
    lead.stage = to_stage
    lead.lost_reason = lost_reason if to_stage == LeadStage.lost else None
    return True


def advance_to(db: Session, lead: Lead | None, to_stage: LeadStage, user: User) -> bool:
    """Move forward only: an offer shouldn't drag a Won or Lost lead back into Negotiation."""
    if lead is None or lead.stage in (LeadStage.won, LeadStage.lost):
        return False
    if ORDER.index(lead.stage) >= ORDER.index(to_stage):
        return False
    return move(db, lead, to_stage, user)
