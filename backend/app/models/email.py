from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EmailLog(Base):
    """Every automatic email we try to send, and what happened.

    The unique constraint is what makes "send once" reliable: a client gets at
    most one introduction for each agent who looks after them.
    """
    __tablename__ = "email_log"
    __table_args__ = (UniqueConstraint("client_id", "agent_id", "kind", name="uq_email_once_per_agent"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(40))            # "agent_intro"
    to_email: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20))           # sent, failed, skipped
    detail: Mapped[str | None] = mapped_column(Text)          # provider message id, or why it failed / was skipped
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
