"""Automatic emails, sent through Brevo's web API.

Why an API and not SMTP: Render's free plan blocks outgoing SMTP ports, but
ordinary HTTPS calls work everywhere. Without BREVO_API_KEY nothing is sent
(local development and tests), and the reason is recorded instead.
"""
import html
import logging
from dataclasses import dataclass

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Client, EmailLog, User

log = logging.getLogger(__name__)
BREVO_URL = "https://api.brevo.com/v3/smtp/email"
INTRO = "agent_intro"


@dataclass
class Outcome:
    status: str        # sent, failed, skipped
    detail: str


def send_email(to_email: str, to_name: str, subject: str, html_body: str, text_body: str,
               reply_to: tuple[str, str] | None = None) -> Outcome:
    s = get_settings()
    if not s.brevo_api_key or not s.email_from_address:
        return Outcome("skipped", "Email isn’t set up (BREVO_API_KEY or EMAIL_FROM_ADDRESS missing).")
    payload = {
        "sender": {"name": s.email_from_name, "email": s.email_from_address},
        "to": [{"email": to_email, "name": to_name}],
        "subject": subject, "htmlContent": html_body, "textContent": text_body,
    }
    if reply_to:
        payload["replyTo"] = {"email": reply_to[0], "name": reply_to[1]}
    try:
        r = httpx.post(BREVO_URL, json=payload, timeout=s.email_timeout_seconds,
                       headers={"api-key": s.brevo_api_key, "accept": "application/json"})
    except httpx.HTTPError as exc:
        return Outcome("failed", f"Couldn’t reach the email service ({exc.__class__.__name__}).")
    if r.status_code >= 400:
        try:
            msg = r.json().get("message", "")
        except ValueError:
            msg = ""
        return Outcome("failed", f"The email service said no (error {r.status_code}). {msg}".strip())
    try:
        mid = r.json().get("messageId", "")
    except ValueError:
        mid = ""
    return Outcome("sent", f"Sent. {mid}".strip())


def intro_message(client: Client, agent: User) -> tuple[str, str, str]:
    """Subject, HTML and plain text of the "meet your agent" email.
    Names come from forms, so everything is escaped before it goes into HTML."""
    first = client.first_name.strip() or "there"
    agent_first = agent.full_name.split()[0]
    wants = {"seller": "selling your home", "both": "buying and selling"}.get(client.client_type.value, "finding your next home")
    where = f" in {client.preferred_city}" if client.preferred_city else ""
    subject = f"Meet your PropConnect agent, {agent_first}"
    text = (f"Hi {first},\n\n"
            f"Thanks for reaching out to PropConnect AI. {agent.full_name} will be helping you with {wants}{where}.\n\n"
            f"{agent_first} will be in touch soon. You can also reach them at {agent.email}, "
            f"or simply reply to this email.\n\n"
            f"Talk soon,\nPropConnect AI\n\n"
            f"You’re receiving this because you asked PropConnect AI to contact you about your home search.")
    e = html.escape
    body = f"""<div style="font-family:Arial,Helvetica,sans-serif;max-width:560px;margin:0 auto;color:#1c2b3a;line-height:1.55">
  <div style="background:#1c2b3a;padding:18px 24px;border-radius:10px 10px 0 0">
    <span style="color:#ffffff;font-size:18px;font-weight:600">PropConnect <span style="color:#e0a94a">AI</span></span>
  </div>
  <div style="border:1px solid #e3e1da;border-top:0;border-radius:0 0 10px 10px;padding:24px">
    <p style="margin:0 0 14px">Hi {e(first)},</p>
    <p style="margin:0 0 14px">Thanks for reaching out to PropConnect AI. <b>{e(agent.full_name)}</b> will be helping you with {e(wants)}{e(where)}.</p>
    <p style="margin:0 0 14px">{e(agent_first)} will be in touch soon. You can also reach them at
      <a href="mailto:{e(agent.email)}" style="color:#a8741a">{e(agent.email)}</a>, or simply reply to this email.</p>
    <p style="margin:0">Talk soon,<br>PropConnect AI</p>
  </div>
  <p style="font-size:12px;color:#6b7785;margin:14px 4px 0">You’re receiving this because you asked PropConnect AI to contact you about your home search.</p>
</div>"""
    return subject, body, text


def send_agent_intro(db: Session, client: Client, agent: User) -> Outcome:
    """Introduce the client to their new agent, at most once per client and agent.

    The log row is claimed before anything is sent, so even two brokers clicking
    at the same moment can't send the same introduction twice.
    """
    row = db.scalar(select(EmailLog).where(EmailLog.client_id == client.id, EmailLog.agent_id == agent.id,
                                           EmailLog.kind == INTRO))
    if row and row.status in ("sent", "sending"):
        return Outcome("skipped", "This client was already introduced to this agent.")
    try:
        if row is None:
            row = EmailLog(client_id=client.id, agent_id=agent.id, kind=INTRO, to_email=client.email, status="sending")
            db.add(row)
        else:  # an earlier attempt failed or was skipped: try again
            row.status, row.to_email = "sending", client.email
        db.commit()
    except IntegrityError:
        db.rollback()
        return Outcome("skipped", "This client was already introduced to this agent.")

    if not client.email:
        outcome = Outcome("skipped", "The client has no email address.")
    else:
        subject, body, text = intro_message(client, agent)
        outcome = send_email(client.email, f"{client.first_name} {client.last_name}", subject, body, text,
                             reply_to=(agent.email, agent.full_name))
    if outcome.status != "sent":
        log.warning("Agent intro for client %s not sent: %s", client.id, outcome.detail)
    row.status, row.detail = outcome.status, outcome.detail
    db.commit()
    return outcome
