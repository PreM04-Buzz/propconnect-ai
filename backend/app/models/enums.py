import enum


class UserRole(str, enum.Enum):
    agent = "agent"
    admin = "admin"  # Administrator / Broker


class ClientType(str, enum.Enum):
    buyer = "buyer"
    seller = "seller"
    both = "both"


class FinancingStatus(str, enum.Enum):
    unknown = "unknown"
    not_started = "not_started"
    pre_qualified = "pre_qualified"
    pre_approved = "pre_approved"
    cash = "cash"


class LeadStage(str, enum.Enum):
    new = "new"
    contacted = "contacted"
    qualified = "qualified"
    proposal = "proposal"
    negotiation = "negotiation"
    won = "won"
    lost = "lost"


class PropertyStatus(str, enum.Enum):
    for_sale = "for_sale"
    sold = "sold"
    ready_to_build = "ready_to_build"
    off_market = "off_market"


class InteractionType(str, enum.Enum):
    call = "call"
    email = "email"
    text = "text"
    meeting = "meeting"
    note = "note"


class AppointmentType(str, enum.Enum):
    viewing = "viewing"
    meeting = "meeting"
    follow_up = "follow_up"


class AppointmentStatus(str, enum.Enum):
    scheduled = "scheduled"
    completed = "completed"
    cancelled = "cancelled"
    no_show = "no_show"


class OfferStatus(str, enum.Enum):
    draft = "draft"
    submitted = "submitted"
    countered = "countered"
    accepted = "accepted"
    rejected = "rejected"
    withdrawn = "withdrawn"


class SuggestionStatus(str, enum.Enum):
    suggested = "suggested"
    accepted = "accepted"
    dismissed = "dismissed"


class SuggestionSource(str, enum.Enum):
    openai = "openai"
    rules = "rules"  # deterministic fallback when the AI is unavailable
