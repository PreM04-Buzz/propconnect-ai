"""Create the first Administrator/Broker account.  Run from backend/: python -m app.scripts.seed"""
from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import User
from app.models.enums import UserRole


def main() -> None:
    s = get_settings()
    with SessionLocal() as db:
        email = s.admin_email.lower()
        if db.scalar(select(User).where(User.email == email)):
            print(f"Admin {email} already exists, nothing to do.")
            return
        db.add(User(email=email, full_name="Broker Admin", role=UserRole.admin,
                    hashed_password=hash_password(s.admin_password)))
        db.commit()
        print(f"Created admin {email}")


if __name__ == "__main__":
    main()
