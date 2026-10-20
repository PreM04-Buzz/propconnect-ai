import pytest

from app.core.config import DEV_SECRET, Settings, check_production_settings
from app.models.enums import UserRole
from tests.conftest import login, make_user


def test_login_locks_after_five_failures(client, db):
    make_user(db, "agent@test.com", UserRole.agent)
    for _ in range(5):
        r = client.post("/api/auth/login", data={"username": "agent@test.com", "password": "wrong"})
        assert r.status_code == 401
    # even the right password is refused while locked
    r = client.post("/api/auth/login", data={"username": "agent@test.com", "password": "password123"})
    assert r.status_code == 429


def test_a_successful_login_clears_earlier_failures(client, db):
    make_user(db, "agent@test.com", UserRole.agent)
    for _ in range(4):
        client.post("/api/auth/login", data={"username": "agent@test.com", "password": "wrong"})
    login(client, "agent@test.com")
    for _ in range(4):
        assert client.post("/api/auth/login", data={"username": "agent@test.com", "password": "wrong"}).status_code == 401


def test_change_own_password(client, db):
    make_user(db, "agent@test.com", UserRole.agent)
    headers = login(client, "agent@test.com")
    bad = client.post("/api/users/me/password", headers=headers,
                      json={"current_password": "nope-nope", "new_password": "brand-new-pass"})
    assert bad.status_code == 400
    ok = client.post("/api/users/me/password", headers=headers,
                     json={"current_password": "password123", "new_password": "brand-new-pass"})
    assert ok.status_code == 204
    assert client.post("/api/auth/login", data={"username": "agent@test.com", "password": "password123"}).status_code == 401
    login(client, "agent@test.com", "brand-new-pass")


def test_production_refuses_development_secrets():
    with pytest.raises(RuntimeError):
        check_production_settings(Settings(environment="production", jwt_secret=DEV_SECRET, admin_password="x" * 12))
    with pytest.raises(RuntimeError):
        check_production_settings(Settings(environment="production", jwt_secret="y" * 48, admin_password="change-me-now"))
    check_production_settings(Settings(environment="production", jwt_secret="y" * 48, admin_password="x" * 12))
    check_production_settings(Settings(environment="development", jwt_secret=DEV_SECRET))
