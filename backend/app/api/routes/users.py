from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.api.deps import AdminUser, CurrentUser, DbSession
from app.core.security import hash_password, verify_password
from app.models import User
from app.models.enums import UserRole
from app.schemas.admin import UserUpdate
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


@router.patch("/{user_id}", response_model=UserRead)
def update_user(user_id: int, payload: UserUpdate, db: DbSession, broker: AdminUser) -> User:
    """Brokers rename people, change agent and broker roles, and deactivate or reactivate accounts.
    A deactivated person can’t sign in; their clients stay with them until reassigned."""
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found.")
    data = payload.model_dump(exclude_unset=True)
    demoting = data.get("role") not in (None, UserRole.admin)
    deactivating = data.get("is_active") is False
    if target.id == broker.id and (demoting or deactivating):
        raise HTTPException(status.HTTP_409_CONFLICT, "You can’t deactivate or demote your own account.")
    if target.role == UserRole.admin and target.is_active and (demoting or deactivating):
        others = db.scalar(select(func.count()).select_from(User).where(
            User.role == UserRole.admin, User.is_active.is_(True), User.id != target.id))
        if not others:
            raise HTTPException(status.HTTP_409_CONFLICT, "Keep at least one active broker.")
    for key, value in data.items():
        if value is not None:
            setattr(target, key, value.strip() if isinstance(value, str) else value)
    db.commit()
    db.refresh(target)
    return target
