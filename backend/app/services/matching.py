"""Rule-based property matching (0-100), weights from the design document:
budget 30, location 25, bedrooms 15, bathrooms 10, size 10, availability/type 10.
"""
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Client, Property
from app.models.enums import PropertyStatus


@dataclass
class Match:
    property: Property
    score: int
    reasons: list[str]


def score_property(client: Client, p: Property) -> Match:
    score, reasons = 0, []
    price = float(p.price or 0)
    budget = float(client.budget_max) if client.budget_max else None

    if budget:
        if price <= budget:
            score += 30
            reasons.append("Within budget")
        elif price <= budget * 1.05:
            score += 20
            reasons.append("Up to 5% over budget")
        elif price <= budget * 1.10:
            score += 10
            reasons.append("Up to 10% over budget")
    else:
        score += 15

    if client.preferred_city and p.city and client.preferred_city.lower() == p.city.lower():
        score += 25
        reasons.append(f"In {p.city}")
    elif client.preferred_zip and p.zip_code == client.preferred_zip:
        score += 25
        reasons.append(f"In ZIP {p.zip_code}")
    elif client.preferred_state and p.state and client.preferred_state.lower() == p.state.lower():
        score += 10

    if client.min_bedrooms is None or (p.bedrooms or 0) >= client.min_bedrooms:
        score += 15
        if client.min_bedrooms:
            reasons.append(f"{p.bedrooms} bedrooms")
    elif (p.bedrooms or 0) == client.min_bedrooms - 1:
        score += 7

    if client.min_bathrooms is None or float(p.bathrooms or 0) >= float(client.min_bathrooms):
        score += 10
    if client.min_house_size_sqft is None or (p.house_size_sqft or 0) >= client.min_house_size_sqft:
        score += 10

    if p.status == PropertyStatus.for_sale:
        score += 10
    return Match(property=p, score=min(score, 100), reasons=reasons)


def top_matches(db: Session, client: Client, limit: int = 5) -> list[Match]:
    q = select(Property).where(Property.status == PropertyStatus.for_sale)
    if client.preferred_state:
        q = q.where(Property.state.ilike(client.preferred_state))
    if client.budget_max:
        q = q.where(Property.price <= float(client.budget_max) * 1.10)
    candidates = list(db.scalars(q.limit(3000)))
    ranked = sorted((score_property(client, p) for p in candidates),
                    key=lambda m: (-m.score, abs(float(m.property.price or 0) - float(client.budget_max or 0))))
    return ranked[:limit]
