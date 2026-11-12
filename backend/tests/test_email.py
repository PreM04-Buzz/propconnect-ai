import httpx

from app.core.config import get_settings
from app.models import EmailLog
from app.models.enums import UserRole
from app.services import email as email_service
from tests.conftest import login, make_user

FORM = {"first_name": "Dana", "last_name": "Brooks", "email": "dana@example.com", "client_type": "buyer",
        "preferred_city": "Chicago", "budget_max": 400000, "consent": True}


class FakeBrevo:
    """Stands in for Brevo's API and remembers what would have been sent."""
    def __init__(self, status=201):
        self.sent, self.status = [], status

    def __call__(self, url, json, timeout, headers):
        self.sent.append({"url": url, "json": json, "headers": headers})
        return httpx.Response(self.status, json={"messageId": "<abc@brevo>"} if self.status < 400 else {"message": "bad sender"})


def _setup(client, db, monkeypatch, status=201):
    s = get_settings()
    monkeypatch.setattr(s, "brevo_api_key", "test-key")
    monkeypatch.setattr(s, "email_from_address", "hello@propconnect-demo.com")
    fake = FakeBrevo(status)
    monkeypatch.setattr(email_service.httpx, "post", fake)
    make_user(db, "broker@test.com", UserRole.admin)
    a = make_user(db, "maria@test.com", UserRole.agent)
    b = make_user(db, "james@test.com", UserRole.agent)
    client.post("/api/public/intake", json=FORM)
    cid = client.get("/api/admin/clients", headers=login(client, "broker@test.com")).json()[0]["client_id"]
    fake.sent.clear()  # the form's own "we've received your request" email; these tests are about the intro
    return login(client, "broker@test.com"), a, b, cid, fake


def _assign(client, headers, cid, agent_id):
    return client.post(f"/api/admin/clients/{cid}/assign", headers=headers, json={"agent_id": agent_id})


def test_assigning_sends_one_introduction_to_the_client(client, db, monkeypatch):
    broker, a, _, cid, fake = _setup(client, db, monkeypatch)
    r = _assign(client, broker, cid, a.id)
    assert r.status_code == 200 and r.json()["email_status"] == "sent"
    assert len(fake.sent) == 1
    msg = fake.sent[0]["json"]
    assert msg["to"] == [{"email": "dana@example.com", "name": "Dana Brooks"}]
    assert msg["replyTo"]["email"] == "maria@test.com"            # replies go straight to the agent
    assert msg["sender"]["email"] == "hello@propconnect-demo.com"
    assert a.full_name.split()[0] in msg["subject"] and "Chicago" in msg["textContent"]
    assert fake.sent[0]["headers"]["api-key"] == "test-key"
    assert db.query(EmailLog).one().status == "sent"
    assert client.get("/api/admin/clients", headers=broker, params={"show": "all"}).json()[0]["intro_email"] == "sent"


def test_each_agent_introduces_themselves_only_once(client, db, monkeypatch):
    broker, a, b, cid, fake = _setup(client, db, monkeypatch)
    _assign(client, broker, cid, a.id)          # intro from Maria
    _assign(client, broker, cid, b.id)          # moved: intro from James
    r = _assign(client, broker, cid, a.id)      # back to Maria: no second email
    assert r.json()["email_status"] == "skipped"
    assert [m["json"]["replyTo"]["email"] for m in fake.sent] == ["maria@test.com", "james@test.com"]


def test_without_email_set_up_the_assignment_still_works(client, db, monkeypatch):
    broker, a, _, cid, fake = _setup(client, db, monkeypatch)
    monkeypatch.setattr(get_settings(), "brevo_api_key", None)
    r = _assign(client, broker, cid, a.id)
    assert r.status_code == 200 and r.json()["agent_id"] == a.id
    assert r.json()["email_status"] == "skipped" and "set up" in r.json()["email_detail"]
    assert fake.sent == []


def test_if_the_email_service_refuses_the_assignment_still_works_and_can_retry(client, db, monkeypatch):
    broker, a, b, cid, fake = _setup(client, db, monkeypatch, status=400)
    r = _assign(client, broker, cid, a.id)
    assert r.status_code == 200 and r.json()["agent_id"] == a.id and r.json()["email_status"] == "failed"
    fake.status = 201
    _assign(client, broker, cid, b.id)
    r = _assign(client, broker, cid, a.id)      # a failed intro is retried when assigned again
    assert r.json()["email_status"] == "sent"


def test_the_email_service_being_unreachable_doesnt_break_assignment(client, db, monkeypatch):
    broker, a, _, cid, _ = _setup(client, db, monkeypatch)
    def down(*args, **kwargs):
        raise httpx.ConnectTimeout("no route")
    monkeypatch.setattr(email_service.httpx, "post", down)
    r = _assign(client, broker, cid, a.id)
    assert r.status_code == 200 and r.json()["email_status"] == "failed"


def test_names_are_escaped_in_the_html(client, db, monkeypatch):
    broker, a, _, _, fake = _setup(client, db, monkeypatch)
    client.post("/api/public/intake", json={**FORM, "email": "x@example.com", "first_name": "<b>Eve</b>"})
    cid = [r for r in client.get("/api/admin/clients", headers=broker).json() if r["email"] == "x@example.com"][0]["client_id"]
    _assign(client, broker, cid, a.id)
    assert "<b>Eve</b>" not in fake.sent[-1]["json"]["htmlContent"]
    assert "&lt;b&gt;Eve&lt;/b&gt;" in fake.sent[-1]["json"]["htmlContent"]


def test_no_email_address_means_no_email(client, db, monkeypatch):
    broker, a, _, _, fake = _setup(client, db, monkeypatch)
    agent = login(client, "maria@test.com")
    r = client.post("/api/clients", headers=agent, json={"first_name": "No", "last_name": "Email", "client_type": "buyer"})
    cid = r.json()["id"]
    b = make_user(db, "priya@test.com", UserRole.agent)
    r = _assign(client, broker, cid, b.id)
    assert r.json()["email_status"] == "skipped" and "no email" in r.json()["email_detail"]
    assert all(m["json"]["to"][0]["email"] != "" for m in fake.sent)


def _link(msg: dict) -> str:
    import re
    return re.search(r'href="([^"]+portal[^"]*)"', msg["json"]["htmlContent"]).group(1).replace("&amp;", "&")


def test_the_form_emails_a_link_to_create_an_account(client, db, monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "brevo_api_key", "test-key")
    monkeypatch.setattr(s, "email_from_address", "hello@propconnect-demo.com")
    fake = FakeBrevo()
    monkeypatch.setattr(email_service.httpx, "post", fake)
    r = client.post("/api/public/intake", json=FORM)
    assert r.status_code == 202 and "create your client account" in r.json()["message"]
    [msg] = fake.sent
    assert msg["json"]["subject"] == "We’ve received your request" and msg["json"]["to"][0]["email"] == "dana@example.com"
    assert "Create my client account" in msg["json"]["htmlContent"]
    url = _link(msg)
    assert "/portal/setup#token=" in url
    token = url.split("#token=", 1)[1]
    assert client.post("/api/portal/accept", json={"token": token, "password": "dana-pass-123"}).status_code == 200


def test_a_returning_client_with_an_account_gets_a_sign_in_link_not_a_reset(client, db, monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "brevo_api_key", "test-key")
    monkeypatch.setattr(s, "email_from_address", "hello@propconnect-demo.com")
    fake = FakeBrevo()
    monkeypatch.setattr(email_service.httpx, "post", fake)
    client.post("/api/public/intake", json=FORM)
    token = _link(fake.sent[0]).split("#token=", 1)[1]
    client.post("/api/portal/accept", json={"token": token, "password": "dana-pass-123"})
    client.post("/api/public/intake", json={**FORM, "notes": "Now also Evanston"})
    second = fake.sent[-1]["json"]["htmlContent"]
    assert "Sign in to your client portal" in second and "#token=" not in second
    ok = client.post("/api/portal/login", json={"email": "dana@example.com", "password": "dana-pass-123"})
    assert ok.status_code == 200                                  # the password was not touched


def test_the_intro_email_has_a_create_link_then_a_sign_in_link(client, db, monkeypatch):
    broker, a, b, cid, fake = _setup(client, db, monkeypatch)
    _assign(client, broker, cid, a.id)
    intro = fake.sent[-1]
    assert "Create my client account" in intro["json"]["htmlContent"]
    token = _link(intro).split("#token=", 1)[1]
    assert client.post("/api/portal/accept", json={"token": token, "password": "dana-pass-123"}).status_code == 200
    _assign(client, broker, cid, b.id)                            # moved: James introduces himself
    second = fake.sent[-1]["json"]["htmlContent"]
    assert "Sign in to your client portal" in second and "#token=" not in second


def test_the_form_still_works_when_email_fails(client, db, monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "brevo_api_key", "test-key")
    monkeypatch.setattr(s, "email_from_address", "hello@propconnect-demo.com")
    def down(*args, **kwargs):
        raise httpx.ConnectTimeout("no route")
    monkeypatch.setattr(email_service.httpx, "post", down)
    assert client.post("/api/public/intake", json=FORM).status_code == 202
