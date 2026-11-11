"""The broker's admin area: the team, and who looks after which client."""
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.api.deps import AdminUser, DbSession
from app.models import Appointment, Client, EmailLog, Interaction, Lead, User
from app.models.enums import AppointmentStatus, InteractionType, LeadStage
from app.schemas.admin import AssignmentRow, AssignRequest, AssignResult, TeamMember
from app.services.email import INTRO, send_agent_intro

router = APIRouter(prefix="/admin", tags=["admin"])

OPEN = [s for s in LeadStage if s not in (LeadStage.won, LeadStage.lost)]


def _utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


@router.get("/team", response_model=list[TeamMember])
def team(db: DbSession, _: AdminUser) -> list[TeamMember]:
    """Everyone on the team, with how much each person is looking after."""
    now = datetime.now(timezone.utc)
    clients = dict(db.execute(select(Client.agent_id, func.count()).group_by(Client.agent_id)).all())
    leads = dict(db.execute(select(Lead.agent_id, func.count()).where(Lead.stage.in_(OPEN)).group_by(Lead.agent_id)).all())
    appts = dict(db.execute(select(Appointment.agent_id, func.count()).where(
        Appointment.status == AppointmentStatus.scheduled, Appointment.starts_at >= now).group_by(Appointment.agent_id)).all())
    return [TeamMember(id=u.id, full_name=u.full_name, email=u.email, role=u.role, is_active=u.is_active,
                       created_at=u.created_at, clients=clients.get(u.id, 0), open_leads=leads.get(u.id, 0),
                       upcoming_appointments=appts.get(u.id, 0))
            for u in db.scalars(select(User).order_by(User.is_active.desc(), User.full_name))]


def _row(db, c: Client) -> AssignmentRow:
    lead = db.scalar(select(Lead).where(Lead.client_id == c.id).order_by(Lead.id.desc()))
    agent = db.get(User, c.agent_id) if c.agent_id else None
    intro = db.scalar(select(EmailLog.status).where(EmailLog.client_id == c.id, EmailLog.agent_id == c.agent_id,
                                                    EmailLog.kind == INTRO)) if c.agent_id else None
    return AssignmentRow(
        client_id=c.id, client_name=f"{c.first_name} {c.last_name}", email=c.email, phone=c.phone,
        client_type=c.client_type, preferred_city=c.preferred_city,
        budget_max=float(c.budget_max) if c.budget_max is not None else None, created_at=c.created_at,
        from_website=c.consent_at is not None, lead_id=lead.id if lead else None, lead_stage=lead.stage if lead else None,
        agent_id=c.agent_id, agent_name=agent.full_name if agent else None, intro_email=intro)


@router.get("/clients", response_model=list[AssignmentRow])
def clients_to_assign(db: DbSession, _: AdminUser,
                      show: str = Query(default="unassigned", pattern="^(unassigned|all)$")) -> list[AssignmentRow]:
    """Website requests waiting for an agent (default), or every client with their agent."""
    q = select(Client)
    if show == "unassigned":
        q = q.where(Client.agent_id.is_(None))
    return [_row(db, c) for c in db.scalars(q.order_by(Client.created_at.desc()).limit(500))]


@router.post("/clients/{client_id}/assign", response_model=AssignResult)
def assign_client(client_id: int, payload: AssignRequest, db: DbSession, broker: AdminUser) -> AssignResult:
    """Give a client to an agent, or move them to another one. Their leads and upcoming
    appointments move with them; refused if an appointment would clash with the new agent's calendar."""
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Client not found.")
    agent = db.get(User, payload.agent_id)
    if agent is None or not agent.is_active:
        raise HTTPException(422, "Pick an active agent or broker.")
    if client.agent_id == agent.id:
        return AssignResult(**_row(db, client).model_dump(), moved_appointments=0,
                            email_status="skipped", email_detail="Already with this agent.")

    now = datetime.now(timezone.utc)
    upcoming = list(db.scalars(select(Appointment).where(
        Appointment.client_id == client.id, Appointment.status == AppointmentStatus.scheduled,
        Appointment.starts_at >= now)))
    for a in upcoming:
        clash = db.scalar(select(Appointment).where(
            Appointment.agent_id == agent.id, Appointment.status == AppointmentStatus.scheduled,
            Appointment.starts_at < a.ends_at, Appointment.ends_at > a.starts_at, Appointment.id != a.id).limit(1))
        if clash:
            when = _utc(clash.starts_at).strftime("%b %d at %H:%M UTC")
            raise HTTPException(status.HTTP_409_CONFLICT,
                                f"{agent.full_name} already has an appointment on {when}, the same time as one of "
                                f"{client.first_name}’s. Move one of them first.")

    previous = db.get(User, client.agent_id) if client.agent_id else None
    client.agent_id = agent.id
    for lead in db.scalars(select(Lead).where(Lead.client_id == client.id)):
        lead.agent_id = agent.id
    for a in upcoming:
        a.agent_id = agent.id
    what = f"Moved from {previous.full_name} to {agent.full_name}" if previous else f"Assigned to {agent.full_name}"
    db.add(Interaction(client_id=client.id, agent_id=agent.id, interaction_type=InteractionType.note,
                       summary=f"{what} by {broker.full_name}.", occurred_at=now))
    db.commit()
    db.refresh(client)
    # The assignment is saved first; the email can never undo it.
    email = send_agent_intro(db, client, agent)
    db.refresh(client)
    return AssignResult(**_row(db, client).model_dump(), moved_appointments=len(upcoming),
                        email_status=email.status, email_detail=email.detail)
