"""All ORM models. Import from here so Alembic sees every table."""
from app.models.crm import (
    Appointment,
    Client,
    Interaction,
    Lead,
    LeadStageHistory,
    Offer,
    PropertyInterest,
)
from app.models.ai import AiSuggestion
from app.models.market import MarketInventory
from app.models.property import Property
from app.models.user import User

__all__ = [
    "AiSuggestion", "Appointment", "Client", "Interaction", "Lead", "LeadStageHistory",
    "MarketInventory", "Offer", "Property", "PropertyInterest", "User",
]
