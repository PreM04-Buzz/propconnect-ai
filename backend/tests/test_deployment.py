from app.core.config import Settings, get_settings
from tests.conftest import new_client


def test_hosted_database_urls_get_the_psycopg_driver():
    neon = "postgresql://u:p@ep-cool-name.us-east-2.aws.neon.tech/neondb?sslmode=require"
    assert Settings(database_url=neon).database_url.startswith("postgresql+psycopg://u:p@ep-cool-name")
    assert Settings(database_url="postgres://u:p@host/db").database_url == "postgresql+psycopg://u:p@host/db"
    local = "postgresql+psycopg://propconnect:propconnect@localhost:5432/propconnect"
    assert Settings(database_url=local).database_url == local


def test_ai_requests_are_capped_per_user(client, agent_headers, monkeypatch):
    monkeypatch.setattr(get_settings(), "ai_requests_per_hour", 2)
    _, lid = new_client(client, agent_headers)
    for _ in range(2):
        assert client.post(f"/api/leads/{lid}/ai/next-step", headers=agent_headers).status_code == 201
    r = client.post(f"/api/leads/{lid}/ai/next-step", headers=agent_headers)
    assert r.status_code == 429 and "limit" in r.json()["detail"]


def test_cors_allows_the_github_pages_site():
    s = Settings(cors_origins="https://prem04-buzz.github.io, http://localhost:5173")
    assert s.cors_origin_list == ["https://prem04-buzz.github.io", "http://localhost:5173"]
