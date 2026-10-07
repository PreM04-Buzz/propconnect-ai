from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession, ensure_owner, is_admin
from app.models import Client, Interaction, Lead, LeadStageHistory, User
from app.models.enums import LeadStage
from app.schemas.client import ClientRead
from app.schemas.lead import (
    LeadCard, LeadCreate, LeadDetail, LeadMove, LeadUpdate, ScoreItemRead, StageCount, StageHistoryRead,
)
from app.services.lead_scoring import compute_score, refresh_client_leads

router = APIRouter(prefix="/leads", tags=["leads"])


def get_lead(db, lead_id: int, user: User) -> Lead:
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lead not found.")
    ensure_owner(user, lead.agent_id)
    return lead


def lead_detail(db, lead: Lead) -> LeadDetail:
    db.refresh(lead)
    score = compute_score(db, lead.client)
    return LeadDetail(
        id=lead.id, stage=lead.stage, source=lead.source, score=lead.score, priority=lead.priority,
        lost_reason=lead.lost_reason, agent_id=lead.agent_id, created_at=lead.created_at, updated_at=lead.updated_at,
        client=ClientRead.model_validate(lead.client),
        history=[StageHistoryRead.model_validate(h) for h in lead.history],
        score_breakdown=[ScoreItemRead(**vars(i)) for i in score.items],
    )


@router.get("", response_model=list[LeadCard])
def list_leads(db: DbSession, user: CurrentUser, stage: LeadStage | None = None,
               q: str | None = Query(default=None, description="Search client name or city")) -> list[LeadCard]:
    last_contact = (select(Interaction.client_id, func.max(Interaction.occurred_at).label("last"))
                    .group_by(Interaction.client_id).subquery())
    query = (select(Lead, Client, last_contact.c.last).join(Client, Client.id == Lead.client_id)
             .outerjoin(last_contact, last_contact.c.client_id == Client.id))
    if not is_admin(user):
        query = query.where(Lead.agent_id == user.id)
    if stage:
        query = query.where(Lead.stage == stage)
    if q:
        like = f"%{q.strip()}%"
        query = query.where((Client.first_name + " " + Client.last_name).ilike(like) | Client.preferred_city.ilike(like))
    rows = db.execute(query.order_by(Lead.score.desc().nulls_last(), Lead.updated_at.desc()).limit(1000)).all()
    return [LeadCard(
        id=l.id, stage=l.stage, source=l.source, score=l.score, priority=l.priority, client_id=c.id,
        client_name=f"{c.first_name} {c.last_name}", client_type=c.client_type.value,
        budget_max=float(c.budget_max) if c.budget_max is not None else None, preferred_city=c.preferred_city,
        last_contact_at=last, updated_at=l.updated_at,
    ) for l, c, last in rows]


@router.get("/summary", response_model=list[StageCount])
def stage_summary(db: DbSession, user: CurrentUser) -> list[StageCount]:
    query = select(Lead.stage, func.count(Lead.id)).group_by(Lead.stage)
    if not is_admin(user):
        query = query.where(Lead.agent_id == user.id)
    counts = dict(db.execute(query).all())
    return [StageCount(stage=s, count=counts.get(s, 0)) for s in LeadStage]


@router.post("", response_model=LeadDetail, status_code=status.HTTP_201_CREATED)
def create_lead(payload: LeadCreate, db: DbSession, user: CurrentUser) -> LeadDetail:
    client = db.get(Client, payload.client_id)
    if client is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Client not found.")
    ensure_owner(user, client.agent_id)
    lead = Lead(client_id=client.id, agent_id=client.agent_id, stage=LeadStage.new, source=payload.source)
    db.add(lead)
    db.flush()
    db.add(LeadStageHistory(lead_id=lead.id, from_stage=None, to_stage=LeadStage.new, changed_by_id=user.id))
    refresh_client_leads(db, client)
    db.commit()
    return lead_detail(db, lead)


@router.get("/{lead_id}", response_model=LeadDetail)
def read_lead(lead_id: int, db: DbSession, user: CurrentUser) -> LeadDetail:
    return lead_detail(db, get_lead(db, lead_id, user))


@router.patch("/{lead_id}", response_model=LeadDetail)
def update_lead(lead_id: int, payload: LeadUpdate, db: DbSession, user: CurrentUser) -> LeadDetail:
    lead = get_lead(db, lead_id, user)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(lead, k, v)
    db.commit()
    return lead_detail(db, lead)


@router.post("/{lead_id}/move", response_model=LeadDetail)
def move_lead(lead_id: int, payload: LeadMove, db: DbSession, user: CurrentUser) -> LeadDetail:
    """Move a lead to another pipeline stage. Every move is recorded in the stage history."""
    lead = get_lead(db, lead_id, user)
    if payload.to_stage == lead.stage:
        return lead_detail(db, lead)
    if payload.to_stage == LeadStage.lost and not (payload.lost_reason or "").strip():
        raise HTTPException(422, "Please give a reason when marking a lead as lost.")
    db.add(LeadStageHistory(lead_id=lead.id, from_stage=lead.stage, to_stage=payload.to_stage, changed_by_id=user.id))
    lead.stage = payload.to_stage
    lead.lost_reason = payload.lost_reason.strip() if payload.to_stage == LeadStage.lost else None
    db.commit()
    return lead_detail(db, lead)
