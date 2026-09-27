from app.models.enums import UserRole
from tests.conftest import login, make_user


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_login_and_me(client, db):
    make_user(db, "agent@test.com", UserRole.agent)
    headers = login(client, "agent@test.com")
    r = client.get("/api/auth/me", headers=headers)
    assert r.status_code == 200
    assert r.json()["role"] == "agent"
    assert "hashed_password" not in r.json()


def test_wrong_password_rejected(client, db):
    make_user(db, "agent@test.com", UserRole.agent)
    r = client.post("/api/auth/login", data={"username": "agent@test.com", "password": "nope"})
    assert r.status_code == 401


def test_me_requires_token(client):
    assert client.get("/api/auth/me").status_code == 401


def test_bad_token_rejected(client):
    r = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert r.status_code == 401


def test_password_is_hashed(db):
    user = make_user(db, "agent@test.com", UserRole.agent)
    assert user.hashed_password != "password123"
    assert user.hashed_password.startswith("$2")


def test_agent_cannot_manage_users(client, db):
    make_user(db, "agent@test.com", UserRole.agent)
    headers = login(client, "agent@test.com")
    assert client.get("/api/users", headers=headers).status_code == 403


def test_admin_can_create_agent(client, db):
    make_user(db, "broker@test.com", UserRole.admin)
    headers = login(client, "broker@test.com")
    body = {"email": "New.Agent@test.com", "full_name": "New Agent", "password": "password123"}
    r = client.post("/api/users", json=body, headers=headers)
    assert r.status_code == 201
    assert r.json()["email"] == "new.agent@test.com"
    assert client.post("/api/users", json=body, headers=headers).status_code == 409
