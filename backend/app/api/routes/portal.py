"""The client portal: clients sign in, follow their progress and message their agent or the broker.

Clients get their own token type. Staff endpoints refuse it, and these endpoints refuse staff
tokens, so the two sides can never reach each other's data.
"""
from datetime import datetime, timezone
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession, ensure_owner, is_admin
from app.core import login_guard, rate_limit
from app.core.config import get_settings
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password
from app.models import Appointment, Client, ClientAccount, Lead, Message, Offer, Property, User
from app.models.enums import AppointmentStatus, LeadStage, OfferStatus
from app.schemas.portal import (
    Channel, Conversation, MessageIn, MessageRead, PortalAccept, PortalAgent, PortalAppointment, PortalInvite,
    PortalLogin, PortalMessageIn, PortalOffer, PortalOverview, PortalStatus, PortalToken, StageStep,
)
from app.services.email import send_email
from app.services.portal_links import issue_setup_link, token_hash

router = APIRouter(prefix="/portal", tags=["client portal"])
staff_router = APIRouter(tags=["client portal (staff)"])
_bearer = OAuth2PasswordBearer(tokenUrl="/api/portal/login", auto_error=True)
_nope = HTTPException(status.HTTP_401_UNAUTHORIZED, "Please sign in again.", headers={"WWW-Authenticate": "Bearer"})

# What each stage means, in the client's words.
STAGES = [
    (LeadStage.new, "Request received", "We’ve received your request and an agent will be in touch soon."),
    (LeadStage.contacted, "Getting to know you", "Your agent has been in touch to understand what you need."),
    (LeadStage.qualified, "Finding homes", "Your agent is looking for homes that fit your budget and wishes."),
    (LeadStage.proposal, "Viewing homes", "You’re viewing homes your agent picked out for you."),
    (LeadStage.negotiation, "Making an offer", "Your agent is negotiating an offer for you."),
    (LeadStage.won, "Agreed", "Congratulations, your deal is agreed! Your agent will guide you through the next steps."),
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _utc(dt: datetime | None) -> datetime | None:
    return None if dt is None else dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def current_client(db: DbSession, token: Annotated[str, Depends(_bearer)]) -> Client:
    try:
        payload = decode_access_token(token)
        account_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise _nope
    if payload.get("typ") != "client":  # staff tokens can't open the portal
        raise _nope
    account = db.get(ClientAccount, account_id)
    if account is None or account.password_hash is None:
        raise _nope
    client = db.get(Client, account.client_id)
    if client is None:
        raise _nope
    return client


PortalClient = Annotated[Client, Depends(current_client)]


def _ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    return fwd.split(",")[0].strip() or (request.client.host if request.client else "unknown")


# ---------------------------------------------------------------- client side

@router.post("/accept", response_model=PortalToken)
def accept_invite(payload: PortalAccept, request: Request, db: DbSession) -> PortalToken:
    """Open the invitation link and choose a password. The link works once."""
    if not rate_limit.allow(f"portal-accept:{_ip(request)}", 10):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many attempts. Please try again in an hour.")
    account = db.scalar(select(ClientAccount).where(ClientAccount.invite_token_hash == token_hash(payload.token)))
    if account is None or not account.invite_expires_at or _utc(account.invite_expires_at) < _now():
        raise HTTPException(400, "This link has expired or was already used. Ask your agent for a new one.")
    account.password_hash = hash_password(payload.password)
    account.invite_token_hash, account.invite_expires_at = None, None
    account.activated_at = account.activated_at or _now()
    account.last_login_at = _now()
    db.commit()
    return PortalToken(access_token=create_access_token(str(account.id), "client", kind="client"))


@router.post("/login", response_model=PortalToken)
def portal_login(payload: PortalLogin, db: DbSession) -> PortalToken:
    email = payload.email.lower()
    key = f"client:{email}"
    if login_guard.is_locked(key):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many attempts. Please wait a minute and try again.")
    accounts = db.scalars(select(ClientAccount).join(Client, Client.id == ClientAccount.client_id)
                          .where(func.lower(Client.email) == email, ClientAccount.password_hash.is_not(None))).all()
    account = next((a for a in accounts if verify_password(payload.password, a.password_hash or "")), None)
    if account is None:
        login_guard.record_failure(key)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "That email and password don’t match.")
    login_guard.reset(key)
    account.last_login_at = _now()
    db.commit()
    return PortalToken(access_token=create_access_token(str(account.id), "client", kind="client"))


@router.get("/me", response_model=PortalOverview)
def overview(db: DbSession, client: PortalClient) -> PortalOverview:
    """Everything the client may see about their own search, and nothing about anyone else."""
    lead = db.scalar(select(Lead).where(Lead.client_id == client.id).order_by(Lead.id.desc()))
    agent = db.get(User, client.agent_id) if client.agent_id else None
    stage = lead.stage if lead else LeadStage.new
    keys = [s for s, _, _ in STAGES]
    paused = stage == LeadStage.lost
    current = keys.index(stage) if stage in keys else 0
    steps = [StageStep(key=k.value, label=label,
                       state="todo" if paused else "done" if i < current or stage == LeadStage.won else
                       "current" if i == current else "todo")
             for i, (k, label, _) in enumerate(STAGES)]
    if paused:
        label, desc = "Paused", "Your search is paused for now. Send your agent a message whenever you’d like to pick it up again."
    else:
        _, label, desc = STAGES[current]
        if agent is None:
            desc = "We’ve received your request. A broker is choosing the best agent for you."

    now = _now()
    appts = db.execute(select(Appointment, Property).outerjoin(Property, Property.id == Appointment.property_id)
                       .where(Appointment.client_id == client.id, Appointment.status == AppointmentStatus.scheduled,
                              Appointment.starts_at >= now).order_by(Appointment.starts_at).limit(10)).all()
    offers = db.execute(select(Offer, Property).join(Property, Property.id == Offer.property_id)
                        .where(Offer.client_id == client.id, Offer.status != OfferStatus.draft)  # drafts are the agent's work in progress
                        .order_by(Offer.id.desc()).limit(10)).all()

    def addr(p: Property | None) -> str | None:
        return None if p is None else ", ".join(x for x in [p.street_address, p.city] if x) or None

    unread = {ch: db.scalar(select(func.count()).select_from(Message).where(
        Message.client_id == client.id, Message.channel == ch, Message.sender == "staff", Message.read_at.is_(None))) or 0
        for ch in ("agent", "broker")}
    return PortalOverview(
        first_name=client.first_name, last_name=client.last_name, email=client.email,
        agent=PortalAgent(name=agent.full_name, email=agent.email) if agent else None,
        stage=stage.value, stage_label=label, stage_description=desc, paused=paused, steps=steps,
        appointments=[PortalAppointment(starts_at=a.starts_at, ends_at=a.ends_at, kind=a.appointment_type.value,
                                        address=addr(p)) for a, p in appts],
        offers=[PortalOffer(address=addr(p), amount=float(o.amount),
                            counter_amount=float(o.counter_amount) if o.counter_amount is not None else None,
                            status=o.status.value, updated_at=o.decided_at or o.submitted_at) for o, p in offers],
        unread=unread)


def _read(db, msgs: list[Message]) -> list[MessageRead]:
    names = {u.id: u.full_name for u in db.scalars(select(User).where(
        User.id.in_({m.staff_user_id for m in msgs if m.staff_user_id})))}
    return [MessageRead(id=m.id, channel=m.channel, sender=m.sender, body=m.body, created_at=m.created_at, read_at=m.read_at,
                        sender_name=names.get(m.staff_user_id, "PropConnect") if m.sender == "staff" else "Client")
            for m in msgs]


def _thread(db, client_id: int, channel: str) -> list[Message]:
    return list(db.scalars(select(Message).where(Message.client_id == client_id, Message.channel == channel)
                           .order_by(Message.created_at, Message.id).limit(500)))


@router.get("/messages", response_model=list[MessageRead])
def portal_messages(db: DbSession, client: PortalClient, channel: Channel = Query()) -> list[MessageRead]:
    msgs = _thread(db, client.id, channel)
    for m in msgs:
        if m.sender == "staff" and m.read_at is None:
            m.read_at = _now()
    db.commit()
    return _read(db, msgs)


@router.post("/messages", response_model=MessageRead, status_code=status.HTTP_201_CREATED)
def portal_send(payload: PortalMessageIn, db: DbSession, client: PortalClient) -> MessageRead:
    if not rate_limit.allow(f"portal-msg:{client.id}", 30):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "You’ve sent a lot of messages this hour. Please wait a little.")
    if payload.channel == "agent" and client.agent_id is None:
        raise HTTPException(409, "You don’t have an agent yet. Send your message to the broker instead.")
    m = Message(client_id=client.id, channel=payload.channel, sender="client", body=payload.body.strip())
    db.add(m)
    db.commit()
    db.refresh(m)
    return _read(db, [m])[0]


# ---------------------------------------------------------------- staff side

def _invite_message(client: Client, agent_name: str, url: str, days: int) -> tuple[str, str, str]:
    import html
    e = html.escape
    subject = "Your PropConnect client portal"
    text = (f"Hi {client.first_name},\n\n{agent_name} has invited you to your PropConnect client portal, where you can "
            f"follow your home search and message your agent.\n\nSet your password here (the link works once and expires "
            f"in {days} days):\n{url}\n\nPropConnect AI")
    body = f"""<div style="font-family:Arial,Helvetica,sans-serif;max-width:560px;margin:0 auto;color:#1c2b3a;line-height:1.55">
  <div style="background:#1c2b3a;padding:18px 24px;border-radius:10px 10px 0 0">
    <span style="color:#fff;font-size:18px;font-weight:600">PropConnect <span style="color:#e0a94a">AI</span></span></div>
  <div style="border:1px solid #e3e1da;border-top:0;border-radius:0 0 10px 10px;padding:24px">
    <p style="margin:0 0 14px">Hi {e(client.first_name)},</p>
    <p style="margin:0 0 14px">{e(agent_name)} has invited you to your PropConnect client portal, where you can follow your
      home search and message your agent.</p>
    <p style="margin:0 0 18px"><a href="{e(url)}" style="background:#e0a94a;color:#1c2b3a;padding:10px 18px;border-radius:8px;
      text-decoration:none;font-weight:600">Set my password</a></p>
    <p style="margin:0;font-size:13px;color:#6b7785">The link works once and expires in {days} days.</p></div></div>"""
    return subject, body, text


@staff_router.post("/clients/{client_id}/portal-invite", response_model=PortalInvite)
def invite(client_id: int, db: DbSession, user: CurrentUser) -> PortalInvite:
    """Create (or renew) the client's invitation link. Also works as a password reset."""
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Client not found.")
    ensure_owner(user, client.agent_id)
    if not client.email:
        raise HTTPException(422, "Add the client’s email address first: they sign in with it.")
    url, expires = issue_setup_link(db, client, invited_by_id=user.id)
    days = get_settings().portal_invite_days
    subject, body, text = _invite_message(client, user.full_name, url, days)
    sent = send_email(client.email, f"{client.first_name} {client.last_name}", subject, body, text,
                      reply_to=(user.email, user.full_name))
    return PortalInvite(invite_url=url, expires_at=expires, email_status=sent.status,
                        email_detail=sent.detail)


@staff_router.get("/clients/{client_id}/portal", response_model=PortalStatus)
def portal_status(client_id: int, db: DbSession, user: CurrentUser) -> PortalStatus:
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Client not found.")
    ensure_owner(user, client.agent_id)
    a = db.scalar(select(ClientAccount).where(ClientAccount.client_id == client.id))
    return PortalStatus(invited=a is not None, active=bool(a and a.password_hash),
                        invite_expires_at=a.invite_expires_at if a else None,
                        activated_at=a.activated_at if a else None, last_login_at=a.last_login_at if a else None)


def _visible(user: User):
    """Agents see the agent conversation of their own clients; brokers see every conversation."""
    q = select(Message).join(Client, Client.id == Message.client_id)
    if not is_admin(user):
        q = q.where(Message.channel == "agent", Client.agent_id == user.id)
    return q


@staff_router.get("/messages/conversations", response_model=list[Conversation])
def conversations(db: DbSession, user: CurrentUser) -> list[Conversation]:
    msgs = db.scalars(_visible(user).order_by(Message.created_at.desc(), Message.id.desc()).limit(2000)).all()
    seen: dict[tuple[int, str], Conversation] = {}
    unread: dict[tuple[int, str], int] = {}
    for m in msgs:
        key = (m.client_id, m.channel)
        if m.sender == "client" and m.read_at is None:
            unread[key] = unread.get(key, 0) + 1
        if key not in seen:
            c = db.get(Client, m.client_id)
            agent = db.get(User, c.agent_id) if c and c.agent_id else None
            seen[key] = Conversation(client_id=m.client_id, client_name=f"{c.first_name} {c.last_name}" if c else "Client",
                                     channel=m.channel, agent_name=agent.full_name if agent else None,
                                     last_body=m.body[:140], last_sender=m.sender, last_at=m.created_at, unread=0)
    for key, conv in seen.items():
        conv.unread = unread.get(key, 0)
    return sorted(seen.values(), key=lambda c: (c.unread == 0, -c.last_at.timestamp()))


@staff_router.get("/messages/unread-count", response_model=int)
def unread_count(db: DbSession, user: CurrentUser) -> int:
    q = _visible(user).where(Message.sender == "client", Message.read_at.is_(None))
    return db.scalar(select(func.count()).select_from(q.subquery())) or 0


def _staff_thread_access(db, user: User, client_id: int, channel: str) -> Client:
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Client not found.")
    if not is_admin(user):
        ensure_owner(user, client.agent_id)
        if channel != "agent":  # the broker conversation is private from the agent
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found.")
    return client


@staff_router.get("/messages/{client_id}/{channel}", response_model=list[MessageRead])
def staff_thread(client_id: int, channel: Channel, db: DbSession, user: CurrentUser) -> list[MessageRead]:
    _staff_thread_access(db, user, client_id, channel)
    msgs = _thread(db, client_id, channel)
    for m in msgs:
        if m.sender == "client" and m.read_at is None:
            m.read_at = _now()
    db.commit()
    return _read(db, msgs)


@staff_router.post("/messages/{client_id}/{channel}", response_model=MessageRead, status_code=status.HTTP_201_CREATED)
def staff_reply(client_id: int, channel: Channel, payload: MessageIn, db: DbSession, user: CurrentUser) -> MessageRead:
    _staff_thread_access(db, user, client_id, channel)
    m = Message(client_id=client_id, channel=channel, sender="staff", staff_user_id=user.id, body=payload.body.strip())
    db.add(m)
    db.commit()
    db.refresh(m)
    return _read(db, [m])[0]
