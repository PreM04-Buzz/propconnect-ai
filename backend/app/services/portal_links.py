"""Links that bring clients into their portal: one-time "create your account" links and sign-in links.

Only a SHA-256 fingerprint of each token is stored. The token sits after '#' in the link, so it
never reaches a server log, and opening it once uses it up.
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Client, ClientAccount


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def account_for(db: Session, client: Client) -> ClientAccount | None:
    return db.scalar(select(ClientAccount).where(ClientAccount.client_id == client.id))


def is_active(db: Session, client: Client) -> bool:
    a = account_for(db, client)
    return bool(a and a.password_hash)


def sign_in_url() -> str:
    return f"{get_settings().app_url.rstrip('/')}/portal/login"


def issue_setup_link(db: Session, client: Client, invited_by_id: int | None = None) -> tuple[str, datetime]:
    """A fresh one-time link to create (or reset) the client's password. Any older link stops working."""
    account = account_for(db, client)
    if account is None:
        account = ClientAccount(client_id=client.id)
        db.add(account)
    token = secrets.token_urlsafe(32)
    account.invite_token_hash = token_hash(token)
    account.invite_expires_at = datetime.now(timezone.utc) + timedelta(days=get_settings().portal_invite_days)
    if invited_by_id is not None:
        account.invited_by_id = invited_by_id
    db.commit()
    return f"{get_settings().app_url.rstrip('/')}/portal/setup#token={token}", account.invite_expires_at


def portal_link_for_email(db: Session, client: Client) -> tuple[str, str]:
    """(url, button text) to put in an automatic email: sign in if they already have an account,
    otherwise a fresh link to create one."""
    if is_active(db, client):
        return sign_in_url(), "Sign in to your client portal"
    url, _ = issue_setup_link(db, client)
    return url, "Create my client account"
