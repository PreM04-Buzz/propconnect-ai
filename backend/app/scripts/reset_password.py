"""Reset any user's password.  Run from backend/:
    python -m app.scripts.reset_password admin@propconnect-demo.com NewPassword123
"""
import sys

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import User


def main() -> None:
    if len(sys.argv) != 3 or len(sys.argv[2]) < 8:
        raise SystemExit("Usage: python -m app.scripts.reset_password <email> <new password, 8+ characters>")
    email, password = sys.argv[1].lower(), sys.argv[2]
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            raise SystemExit(f"No user with email {email}")
        user.hashed_password = hash_password(password)
        db.commit()
    print(f"Password reset for {email}")


if __name__ == "__main__":
    main()
