from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import AdminUser, CurrentUser, DbSession
from app.core.security import hash_password, verify_password
from app.models import User
from app.schemas.user import PasswordChange, UserCreate, UserRead

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserRead])
def list_users(db: DbSession, _: AdminUser) -> list[User]:
    return list(db.scalars(select(User).order_by(User.id)))


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: DbSession, _: AdminUser) -> User:
    """Brokers/admins create agent accounts; there is no public sign-up."""
    email = payload.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "A user with this email already exists.")
    user = User(
        email=email,
        full_name=payload.full_name,
        role=payload.role,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
def change_my_password(payload: PasswordChange, db: DbSession, user: CurrentUser) -> None:
    """Anyone can change their own password, as long as they know the current one."""
    if not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Your current password isn't right.")
    if payload.new_password == payload.current_password:
        raise HTTPException(422, "Pick a password different from the current one.")
    user.hashed_password = hash_password(payload.new_password)
    db.commit()
