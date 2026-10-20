from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core import login_guard
from app.core.security import create_access_token, verify_password
from app.models import User
from app.schemas.auth import Token
from app.schemas.user import UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login(db: DbSession, form: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:
    """OAuth2 password flow. `username` is the user's email."""
    email = form.username.lower().strip()
    if login_guard.is_locked(email):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            "Too many failed sign-in attempts. Please wait a minute and try again.")
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(form.password, user.hashed_password):
        login_guard.record_failure(email)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password.")
    login_guard.reset(email)
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account is deactivated.")
    return Token(access_token=create_access_token(str(user.id), user.role.value))


@router.get("/me", response_model=UserRead)
def me(user: CurrentUser) -> User:
    return user
