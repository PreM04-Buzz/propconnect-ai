from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession, ensure_owner, is_admin
from app.models import Appointment, Client, Lead, Property
from app.models.enums import AppointmentStatus, AppointmentType
from app.schemas.appointment import AppointmentCreate, AppointmentRead, AppointmentStatusChange, AppointmentUpdate
from app.services.lead_scoring import refresh_client_leads

router = APIRouter(prefix="/appointments", tags=["appointments"])


def utc(dt: datetime) -> datetime:
    """Store everything in UTC so overlap checks compare like with like."""
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def to_read(db, a: Appointment) -> AppointmentRead:
    client = db.get(Client, a.client_id)
    prop = db.get(Property, a.property_id) if a.property_id else None
    lead_id = db.scalar(select(Lead.id).where(Lead.client_id == a.client_id).order_by(Lead.id))
    return AppointmentRead(
        id=a.id, agent_id=a.agent_id, client_id=a.client_id, client_name=f"{client.first_name} {client.last_name}",
        lead_id=lead_id, property_id=a.property_id,
        property_address=f"{prop.street_address}, {prop.city}" if prop else None,
        appointment_type=a.appointment_type, status=a.status, starts_at=utc(a.starts_at), ends_at=utc(a.ends_at),
        notes=a.notes, outcome=a.outcome,
    )


def get_appointment(db, appointment_id: int, user) -> Appointment:
    a = db.get(Appointment, appointment_id)
    if a is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Appointment not found.")
    ensure_owner(user, a.agent_id)
    return a


def check_conflict(db, agent_id: int, starts: datetime, ends: datetime, ignore_id: int | None = None) -> None:
    """An agent can't be in two places at once: reject overlapping scheduled appointments."""
    q = select(Appointment).where(
        Appointment.agent_id == agent_id, Appointment.status == AppointmentStatus.scheduled,
        Appointment.starts_at < ends, Appointment.ends_at > starts,
    )
    if ignore_id:
        q = q.where(Appointment.id != ignore_id)
    clash = db.scalars(q.limit(1)).first()
    if clash:
        c = db.get(Client, clash.client_id)
        kind = clash.appointment_type.value.replace("_", "-")
        raise HTTPException(status.HTTP_409_CONFLICT,
                            f"That time overlaps your {kind} with {c.first_name} {c.last_name}. "
                            "Pick another time, or move that appointment first.")


@router.get("", response_model=list[AppointmentRead])
def list_appointments(
    db: DbSession, user: CurrentUser,
    start: datetime | None = Query(default=None, description="From this time (e.g. Monday 00:00)"),
    end: datetime | None = Query(default=None, description="Up to this time"),
    client_id: int | None = None,
    agent_id: int | None = Query(default=None, description="Brokers only: one agent's calendar"),
) -> list[AppointmentRead]:
    q = select(Appointment)
    if not is_admin(user):
        q = q.where(Appointment.agent_id == user.id)
    elif agent_id:
        q = q.where(Appointment.agent_id == agent_id)
    if start:
        q = q.where(Appointment.ends_at > utc(start))
    if end:
        q = q.where(Appointment.starts_at < utc(end))
    if client_id:
        q = q.where(Appointment.client_id == client_id)
    return [to_read(db, a) for a in db.scalars(q.order_by(Appointment.starts_at).limit(500))]


@router.post("", response_model=AppointmentRead, status_code=status.HTTP_201_CREATED)
def create_appointment(payload: AppointmentCreate, db: DbSession, user: CurrentUser) -> AppointmentRead:
    client = db.get(Client, payload.client_id)
    if client is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Client not found.")
    ensure_owner(user, client.agent_id)
    if payload.property_id is not None and db.get(Property, payload.property_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Property not found.")
    if payload.appointment_type == AppointmentType.viewing and payload.property_id is None:
        raise HTTPException(422, "Pick the property for a viewing.")
    starts, ends = utc(payload.starts_at), utc(payload.ends_at)
    check_conflict(db, client.agent_id, starts, ends)
    a = Appointment(agent_id=client.agent_id, client_id=client.id, property_id=payload.property_id,
                    appointment_type=payload.appointment_type, starts_at=starts, ends_at=ends, notes=payload.notes)
    db.add(a)
    db.flush()
    refresh_client_leads(db, client)
    db.commit()
    db.refresh(a)
    return to_read(db, a)


@router.patch("/{appointment_id}", response_model=AppointmentRead)
def update_appointment(appointment_id: int, payload: AppointmentUpdate, db: DbSession, user: CurrentUser) -> AppointmentRead:
    """Reschedule or edit notes. Only scheduled appointments can be moved."""
    a = get_appointment(db, appointment_id, user)
    data = payload.model_dump(exclude_unset=True)
    if ("starts_at" in data or "ends_at" in data) and a.status != AppointmentStatus.scheduled:
        raise HTTPException(status.HTTP_409_CONFLICT, "Only scheduled appointments can be moved.")
    starts = utc(data.get("starts_at") or a.starts_at)
    ends = utc(data.get("ends_at") or a.ends_at)
    if ends <= starts:
        raise HTTPException(422, "The appointment has to end after it starts.")
    if "property_id" in data and data["property_id"] is not None and db.get(Property, data["property_id"]) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Property not found.")
    check_conflict(db, a.agent_id, starts, ends, ignore_id=a.id)
    a.starts_at, a.ends_at = starts, ends
    for k in ("property_id", "notes"):
        if k in data:
            setattr(a, k, data[k])
    db.commit()
    db.refresh(a)
    return to_read(db, a)


@router.post("/{appointment_id}/status", response_model=AppointmentRead)
def change_status(appointment_id: int, payload: AppointmentStatusChange, db: DbSession, user: CurrentUser) -> AppointmentRead:
    """Complete, cancel or mark a no-show. Completed viewings need feedback and count towards the lead score."""
    a = get_appointment(db, appointment_id, user)
    if a.status != AppointmentStatus.scheduled:
        raise HTTPException(status.HTTP_409_CONFLICT, f"This appointment is already {a.status.value.replace('_', ' ')}.")
    if payload.status == AppointmentStatus.scheduled:
        raise HTTPException(422, "Choose completed, cancelled or no_show.")
    outcome = (payload.outcome or "").strip()
    if payload.status == AppointmentStatus.completed and a.appointment_type == AppointmentType.viewing and not outcome:
        raise HTTPException(422, "Add a line of feedback from the viewing before completing it.")
    a.status = payload.status
    a.outcome = outcome or a.outcome
    db.flush()
    refresh_client_leads(db, db.get(Client, a.client_id))
    db.commit()
    db.refresh(a)
    return to_read(db, a)
