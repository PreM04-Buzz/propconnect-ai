from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import or_, select

from app.api.deps import CurrentUser, DbSession, ensure_owner, is_admin
from app.models import Client, Interaction, Lead, LeadStageHistory, Property, PropertyInterest, User
from app.models.enums import LeadStage
from app.schemas.client import (
    ClientCreate, ClientDetail, ClientListItem, ClientRead, ClientUpdate, InteractionCreate, InteractionRead,
    InterestCreate, InterestRead, LeadBrief,
)
from app.schemas.property import PropertyMatch
from app.services.lead_scoring import refresh_client_leads
from app.services.matching import top_matches

router = APIRouter(prefix="/clients", tags=["clients"])


def get_client(db, client_id: int, user: User) -> Client:
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Client not found.")
    ensure_owner(user, client.agent_id)
    return client


@router.get("", response_model=list[ClientListItem])
def list_clients(
    db: DbSession, user: CurrentUser,
    q: str | None = Query(default=None, description="Search name, email, phone or city"),
    client_type: str | None = None,
    stage: LeadStage | None = None,
) -> list[ClientListItem]:
    query = select(Client, Lead).outerjoin(Lead, Lead.client_id == Client.id)
    if not is_admin(user):
        query = query.where(Client.agent_id == user.id)
    if q:
        like = f"%{q.strip()}%"
        query = query.where(or_(Client.first_name.ilike(like), Client.last_name.ilike(like), Client.email.ilike(like),
                                Client.phone.ilike(like), Client.preferred_city.ilike(like)))
    if client_type:
        query = query.where(Client.client_type == client_type)
    if stage:
        query = query.where(Lead.stage == stage)
    rows = db.execute(query.order_by(Client.updated_at.desc(), Client.id.desc()).limit(500)).all()
    seen, out = set(), []
    for c, lead in rows:
        if c.id in seen:
            continue
        seen.add(c.id)
        out.append(ClientListItem(
            id=c.id, first_name=c.first_name, last_name=c.last_name, email=c.email, phone=c.phone,
            client_type=c.client_type, budget_max=float(c.budget_max) if c.budget_max is not None else None,
            preferred_city=c.preferred_city, financing_status=c.financing_status,
            lead_id=lead.id if lead else None, lead_stage=lead.stage if lead else None,
            lead_priority=lead.priority if lead else None, updated_at=c.updated_at,
        ))
    return out


@router.post("", response_model=ClientDetail, status_code=status.HTTP_201_CREATED)
def create_client(payload: ClientCreate, db: DbSession, user: CurrentUser) -> ClientDetail:
    data = payload.model_dump(exclude={"create_lead", "lead_source", "agent_id"})
    agent_id = user.id
    if payload.agent_id is not None:
        if not is_admin(user):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Only brokers can assign clients to other agents.")
        if db.get(User, payload.agent_id) is None:
            raise HTTPException(422, "Agent not found.")
        agent_id = payload.agent_id
    client = Client(agent_id=agent_id, **data)
    db.add(client)
    db.flush()
    if payload.create_lead:
        lead = Lead(client_id=client.id, agent_id=agent_id, stage=LeadStage.new, source=payload.lead_source)
        db.add(lead)
        db.flush()
        db.add(LeadStageHistory(lead_id=lead.id, from_stage=None, to_stage=LeadStage.new, changed_by_id=user.id))
    db.flush()
    refresh_client_leads(db, client)
    db.commit()
    return client_detail(db, client)


def client_detail(db, client: Client) -> ClientDetail:
    db.refresh(client)
    interactions = db.scalars(select(Interaction).where(Interaction.client_id == client.id)
                              .order_by(Interaction.occurred_at.desc()))
    interests = db.scalars(select(PropertyInterest).where(PropertyInterest.client_id == client.id)
                           .order_by(PropertyInterest.id)).unique()
    leads = db.scalars(select(Lead).where(Lead.client_id == client.id).order_by(Lead.id))
    return ClientDetail(
        **ClientRead.model_validate(client).model_dump(),
        leads=[LeadBrief.model_validate(x) for x in leads],
        interactions=[InteractionRead.model_validate(x) for x in interactions],
        interests=[InterestRead.model_validate(x) for x in interests],
    )


@router.get("/{client_id}", response_model=ClientDetail)
def read_client(client_id: int, db: DbSession, user: CurrentUser) -> ClientDetail:
    return client_detail(db, get_client(db, client_id, user))


@router.patch("/{client_id}", response_model=ClientDetail)
def update_client(client_id: int, payload: ClientUpdate, db: DbSession, user: CurrentUser) -> ClientDetail:
    client = get_client(db, client_id, user)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(client, k, v)
    if client.budget_min is not None and client.budget_max is not None and float(client.budget_min) > float(client.budget_max):
        raise HTTPException(422, "Minimum budget can't be higher than maximum budget.")
    db.flush()
    refresh_client_leads(db, client)
    db.commit()
    return client_detail(db, client)


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(client_id: int, db: DbSession, user: CurrentUser) -> None:
    client = get_client(db, client_id, user)
    db.delete(client)
    db.commit()


@router.post("/{client_id}/interactions", response_model=InteractionRead, status_code=status.HTTP_201_CREATED)
def add_interaction(client_id: int, payload: InteractionCreate, db: DbSession, user: CurrentUser) -> Interaction:
    client = get_client(db, client_id, user)
    item = Interaction(client_id=client.id, agent_id=user.id, interaction_type=payload.interaction_type,
                       summary=payload.summary, occurred_at=payload.occurred_at or datetime.now(timezone.utc))
    db.add(item)
    db.flush()
    refresh_client_leads(db, client)
    db.commit()
    db.refresh(item)
    return item


@router.post("/{client_id}/interests", response_model=InterestRead, status_code=status.HTTP_201_CREATED)
def add_interest(client_id: int, payload: InterestCreate, db: DbSession, user: CurrentUser) -> PropertyInterest:
    client = get_client(db, client_id, user)
    if db.get(Property, payload.property_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Property not found.")
    existing = db.scalar(select(PropertyInterest).where(PropertyInterest.client_id == client.id,
                                                        PropertyInterest.property_id == payload.property_id))
    if existing:
        existing.interest_level, existing.notes = payload.interest_level, payload.notes or existing.notes
        item = existing
    else:
        item = PropertyInterest(client_id=client.id, **payload.model_dump())
        db.add(item)
    db.flush()
    refresh_client_leads(db, client)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{client_id}/interests/{interest_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_interest(client_id: int, interest_id: int, db: DbSession, user: CurrentUser) -> None:
    client = get_client(db, client_id, user)
    item = db.get(PropertyInterest, interest_id)
    if item is None or item.client_id != client.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Interest not found.")
    db.delete(item)
    db.flush()
    refresh_client_leads(db, client)
    db.commit()


@router.get("/{client_id}/matches", response_model=list[PropertyMatch])
def client_matches(client_id: int, db: DbSession, user: CurrentUser,
                   limit: int = Query(default=8, ge=1, le=50)) -> list[PropertyMatch]:
    client = get_client(db, client_id, user)
    return [PropertyMatch(property=m.property, score=m.score, reasons=m.reasons)
            for m in top_matches(db, client, limit)]
