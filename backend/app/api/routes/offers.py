from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession, ensure_owner, is_admin
from app.models import Client, Lead, Offer, Property
from app.models.enums import LeadStage, OfferStatus, PropertyStatus
from app.schemas.offer import OfferCreate, OfferRead, OfferStatusChange
from app.services.lead_scoring import refresh_client_leads
from app.services.pipeline import advance_to, move

router = APIRouter(prefix="/offers", tags=["offers"])

S = OfferStatus
# Which status changes make sense. Accepted, rejected and withdrawn are final.
ALLOWED = {
    S.draft: {S.submitted, S.withdrawn},
    S.submitted: {S.countered, S.accepted, S.rejected, S.withdrawn},
    S.countered: {S.submitted, S.accepted, S.rejected, S.withdrawn},
    S.accepted: set(), S.rejected: set(), S.withdrawn: set(),
}


def to_read(db, o: Offer) -> OfferRead:
    c, p = db.get(Client, o.client_id), db.get(Property, o.property_id)
    lead = db.get(Lead, o.lead_id) if o.lead_id else None
    return OfferRead(
        id=o.id, client_id=c.id, client_name=f"{c.first_name} {c.last_name}", property_id=p.id,
        property_address=f"{p.street_address}, {p.city}", list_price=float(p.price) if p.price is not None else None,
        lead_id=o.lead_id, lead_stage=lead.stage if lead else None, amount=float(o.amount),
        counter_amount=float(o.counter_amount) if o.counter_amount is not None else None, status=o.status,
        submitted_at=o.submitted_at, decided_at=o.decided_at, notes=o.notes, created_at=o.created_at,
    )


def get_offer(db, offer_id: int, user) -> tuple[Offer, Client]:
    o = db.get(Offer, offer_id)
    if o is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Offer not found.")
    c = db.get(Client, o.client_id)
    ensure_owner(user, c.agent_id)
    return o, c


@router.get("", response_model=list[OfferRead])
def list_offers(db: DbSession, user: CurrentUser, status_: OfferStatus | None = Query(default=None, alias="status"),
                client_id: int | None = None, lead_id: int | None = None) -> list[OfferRead]:
    q = select(Offer).join(Client, Client.id == Offer.client_id)
    if not is_admin(user):
        q = q.where(Client.agent_id == user.id)
    if status_:
        q = q.where(Offer.status == status_)
    if client_id:
        q = q.where(Offer.client_id == client_id)
    if lead_id:
        q = q.where(Offer.lead_id == lead_id)
    return [to_read(db, o) for o in db.scalars(q.order_by(Offer.id.desc()).limit(500))]


@router.post("", response_model=OfferRead, status_code=status.HTTP_201_CREATED)
def create_offer(payload: OfferCreate, db: DbSession, user: CurrentUser) -> OfferRead:
    """Make an offer for a client. Submitting it moves the client's lead to Negotiation."""
    client = db.get(Client, payload.client_id)
    if client is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Client not found.")
    ensure_owner(user, client.agent_id)
    prop = db.get(Property, payload.property_id)
    if prop is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Property not found.")
    if prop.status != PropertyStatus.for_sale:
        raise HTTPException(status.HTTP_409_CONFLICT, "This property isn't for sale any more.")
    lead = db.scalar(select(Lead).where(Lead.client_id == client.id).order_by(Lead.id.desc()))
    now = datetime.now(timezone.utc)
    o = Offer(client_id=client.id, property_id=prop.id, lead_id=lead.id if lead else None, amount=payload.amount,
              notes=payload.notes, status=S.submitted if payload.submit else S.draft,
              submitted_at=now if payload.submit else None)
    db.add(o)
    if payload.submit:
        advance_to(db, lead, LeadStage.negotiation, user)
    db.commit()
    db.refresh(o)
    return to_read(db, o)


@router.post("/{offer_id}/status", response_model=OfferRead)
def change_status(offer_id: int, payload: OfferStatusChange, db: DbSession, user: CurrentUser) -> OfferRead:
    """Move an offer along. Accepting it closes the deal: the lead is Won and the property is sold."""
    o, client = get_offer(db, offer_id, user)
    new = payload.status
    if new not in ALLOWED[o.status]:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            f"An offer that is {o.status.value} can't be marked {new.value}.")
    lead = db.get(Lead, o.lead_id) if o.lead_id else None
    prop = db.get(Property, o.property_id)
    now = datetime.now(timezone.utc)

    if new == S.countered:
        if not payload.counter_amount:
            raise HTTPException(422, "Enter the seller's counter amount.")
        o.counter_amount = payload.counter_amount
    if new == S.submitted:
        o.amount = payload.amount or o.amount
        o.submitted_at = now
        advance_to(db, lead, LeadStage.negotiation, user)
    if new == S.accepted:
        already = db.scalar(select(Offer.id).where(Offer.property_id == o.property_id, Offer.status == S.accepted,
                                                   Offer.id != o.id))
        if already or prop.status == PropertyStatus.sold:
            raise HTTPException(status.HTTP_409_CONFLICT, "Another offer on this property was already accepted.")
        prop.status = PropertyStatus.sold
        if lead and lead.stage != LeadStage.won:
            move(db, lead, LeadStage.won, user)
    if new in (S.accepted, S.rejected, S.withdrawn):
        o.decided_at = now
    if payload.notes:
        o.notes = payload.notes
    o.status = new
    db.flush()
    refresh_client_leads(db, client)
    db.commit()
    db.refresh(o)
    return to_read(db, o)
