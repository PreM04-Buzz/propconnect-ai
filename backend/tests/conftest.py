import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import User
from app.models.enums import UserRole

engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)
TestingSession = sessionmaker(bind=engine, expire_on_commit=False)


@event.listens_for(engine, "connect")
def _sqlite_fk(dbapi_conn, _):
    # SQLite ignores ON DELETE CASCADE unless foreign keys are switched on.
    dbapi_conn.execute("PRAGMA foreign_keys=ON")


@pytest.fixture()
def db():
    Base.metadata.create_all(engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture()
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def make_user(db, email: str, role: UserRole, password: str = "password123") -> User:
    user = User(email=email, full_name=email.split("@")[0], role=role,
                hashed_password=hash_password(password))
    db.add(user)
    db.commit()
    return user


def login(client, email: str, password: str = "password123") -> dict[str, str]:
    r = client.post("/api/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def agent_headers(client, db):
    make_user(db, "agent@test.com", UserRole.agent)
    return login(client, "agent@test.com")


@pytest.fixture()
def admin_headers(client, db):
    make_user(db, "broker@test.com", UserRole.admin)
    return login(client, "broker@test.com")


def make_property(db, **kw):
    from app.models import Property
    from app.models.enums import PropertyStatus
    data = dict(status=PropertyStatus.for_sale, price=350000, bedrooms=2, bathrooms=2, house_size_sqft=1100,
                street_address="12 Oak St", city="Naperville", state="Illinois", zip_code="60540")
    data.update(kw)
    p = Property(**data)
    db.add(p)
    db.commit()
    return p


BUYER = {
    "first_name": "Aisha", "last_name": "Patel", "email": "aisha@example.com", "client_type": "buyer",
    "budget_min": 300000, "budget_max": 400000, "budget_confirmed": True, "preferred_city": "Naperville",
    "min_bedrooms": 2, "financing_status": "pre_approved", "purchase_timeline_months": 2,
}
