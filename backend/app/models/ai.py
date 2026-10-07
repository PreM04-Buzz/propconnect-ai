from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.enums import SuggestionSource, SuggestionStatus


class AiSuggestion(TimestampMixin, Base):
    """Every AI Next Step suggestion is stored, with the agent's decision.

    This gives an audit trail and the raw material for the Phase 7 evaluation log.
    """

    __tablename__ = "ai_suggestions"

    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    source: Mapped[SuggestionSource] = mapped_column(Enum(SuggestionSource, native_enum=False, length=20))
    model: Mapped[str | None] = mapped_column(String(80))
    intent_level: Mapped[str] = mapped_column(String(10))  # high / medium / low
    summary: Mapped[str] = mapped_column(Text)
    recommended_action: Mapped[str] = mapped_column(Text)
    action_type: Mapped[str] = mapped_column(String(30))  # call, email, schedule_viewing, send_listings, ...
    reasoning: Mapped[str] = mapped_column(Text)
    draft_message: Mapped[str] = mapped_column(Text)
    status: Mapped[SuggestionStatus] = mapped_column(
        Enum(SuggestionStatus, native_enum=False, length=20), default=SuggestionStatus.suggested
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
