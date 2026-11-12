from datetime import datetime, timedelta, timezone

from app.models import ClientAccount
from app.models.enums import UserRole
from tests.conftest import at, login, make_property, make_user, new_client


def _token_from(url: str) -> str:
    assert "#token=" in url  # after the #, so the token never reaches a server log
    return url.split("#token=", 1)[1]


def _portal(client, db, email="aisha@example.com"):
    """An agent, a broker, and a client who has accepted their invitation."""
    make_user(db, "agent@test.com", UserRole.agent)
    make_user(db, "other@test.com", UserRole.agent)
    make_user(db, "broker@test.com", UserRole.admin)
    agent = login(client, "agent@test.com")
    cid, lid = new_client(client, agent, email=email)
    inv = client.post(f"/api/clients/{cid}/portal-invite", headers=agent).json()
    r = client.post("/api/portal/accept", json={"token": _token_from(inv["invite_url"]), "password": "client-pass-1"})
    assert r.status_code == 200
    return agent, cid, lid, {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_invitation_link_works_once(client, db, agent_headers):
    cid, _ = new_client(client, agent_headers)
    inv = client.post(f"/api/clients/{cid}/portal-invite", headers=agent_headers)
    assert inv.status_code == 200 and inv.json()["email_status"] == "skipped"   # no email key in tests
    token = _token_from(inv.json()["invite_url"])
    assert client.post("/api/portal/accept", json={"token": token, "password": "client-pass-1"}).status_code == 200
    again = client.post("/api/portal/accept", json={"token": token, "password": "another-pass-2"})
    assert again.status_code == 400 and "expired or was already used" in again.json()["detail"]
    status_ = client.get(f"/api/clients/{cid}/portal", headers=agent_headers).json()
    assert status_["active"] and status_["activated_at"]


def test_expired_link_is_refused(client, db, agent_headers):
    cid, _ = new_client(client, agent_headers)
    token = _token_from(client.post(f"/api/clients/{cid}/portal-invite", headers=agent_headers).json()["invite_url"])
    acc = db.query(ClientAccount).one()
    acc.invite_expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()
    assert client.post("/api/portal/accept", json={"token": token, "password": "client-pass-1"}).status_code == 400


def test_only_the_clients_agent_or_broker_can_invite(client, db):
    make_user(db, "agent@test.com", UserRole.agent)
    make_user(db, "other@test.com", UserRole.agent)
    agent, other = login(client, "agent@test.com"), login(client, "other@test.com")
    cid, _ = new_client(client, agent)
    assert client.post(f"/api/clients/{cid}/portal-invite", headers=other).status_code == 404
    no_email, _ = new_client(client, agent, email=None)
    r = client.post(f"/api/clients/{no_email}/portal-invite", headers=agent)
    assert r.status_code == 422 and "email" in r.json()["detail"]


def test_sign_in_and_lockout(client, db):
    _portal(client, db)
    ok = client.post("/api/portal/login", json={"email": "AISHA@example.com", "password": "client-pass-1"})
    assert ok.status_code == 200
    for _ in range(5):
        assert client.post("/api/portal/login", json={"email": "aisha@example.com", "password": "wrong"}).status_code == 401
    locked = client.post("/api/portal/login", json={"email": "aisha@example.com", "password": "client-pass-1"})
    assert locked.status_code == 429


def test_client_and_staff_tokens_never_cross(client, db):
    agent, cid, _, me = _portal(client, db)
    assert client.get("/api/clients", headers=me).status_code == 401          # a client can't use the CRM
    assert client.get(f"/api/clients/{cid}", headers=me).status_code == 401
    assert client.get("/api/messages/conversations", headers=me).status_code == 401
    assert client.get("/api/portal/me", headers=agent).status_code == 401     # staff can't open the portal


def test_progress_follows_the_pipeline(client, db):
    agent, _, lid, me = _portal(client, db)
    client.post(f"/api/leads/{lid}/move", headers=agent, json={"to_stage": "proposal"})
    o = client.get("/api/portal/me", headers=me).json()
    assert o["stage_label"] == "Viewing homes"
    assert [s["state"] for s in o["steps"]] == ["done", "done", "done", "current", "todo", "todo"]


def test_overview_shows_progress_viewings_and_offers(client, db):
    agent, cid, lid, me = _portal(client, db)
    p = make_property(db, street_address="48 Maple Ave", city="Naperville")
    client.post(f"/api/leads/{lid}/move", headers=agent, json={"to_stage": "proposal"})
    client.post("/api/appointments", headers=agent, json={"client_id": cid, "property_id": p.id,
                "appointment_type": "viewing", "starts_at": at(2, 10), "ends_at": at(2, 11)})
    client.post("/api/offers", headers=agent, json={"client_id": cid, "property_id": p.id, "amount": 345000})
    o = client.get("/api/portal/me", headers=me).json()
    assert o["first_name"] == "Aisha" and o["agent"]["email"] == "agent@test.com"
    # Creating the offer moved the lead on to negotiation, as it does in the CRM.
    assert o["stage_label"] == "Making an offer"
    assert [s["state"] for s in o["steps"]] == ["done", "done", "done", "done", "current", "todo"]
    assert o["appointments"][0]["address"] == "48 Maple Ave, Naperville" and o["appointments"][0]["kind"] == "viewing"
    assert o["offers"][0]["amount"] == 345000 and o["offers"][0]["status"] == "submitted"
    # A draft offer is the agent's work in progress, so the client doesn't see it yet.
    from app.models import Offer
    from app.models.enums import OfferStatus
    db.query(Offer).update({Offer.status: OfferStatus.draft})
    db.commit()
    assert client.get("/api/portal/me", headers=me).json()["offers"] == []


def test_a_lost_lead_shows_as_paused(client, db):
    agent, _, lid, me = _portal(client, db)
    client.post(f"/api/leads/{lid}/move", headers=agent, json={"to_stage": "lost", "lost_reason": "Bought elsewhere"})
    o = client.get("/api/portal/me", headers=me).json()
    assert o["paused"] and o["stage_label"] == "Paused" and all(s["state"] == "todo" for s in o["steps"])


def test_messages_with_the_agent(client, db):
    agent, cid, _, me = _portal(client, db)
    assert client.post("/api/portal/messages", headers=me, json={"channel": "agent", "body": "Can we see it Saturday?"}).status_code == 201
    assert client.get("/api/messages/unread-count", headers=agent).json() == 1
    [conv] = client.get("/api/messages/conversations", headers=agent).json()
    assert conv["client_id"] == cid and conv["channel"] == "agent" and conv["unread"] == 1
    thread = client.get(f"/api/messages/{cid}/agent", headers=agent).json()       # opening it marks it read
    assert thread[0]["body"] == "Can we see it Saturday?" and client.get("/api/messages/unread-count", headers=agent).json() == 0
    client.post(f"/api/messages/{cid}/agent", headers=agent, json={"body": "Saturday at 11 works."})
    assert client.get("/api/portal/me", headers=me).json()["unread"] == {"agent": 1, "broker": 0}
    mine = client.get("/api/portal/messages", headers=me, params={"channel": "agent"}).json()
    assert [m["sender"] for m in mine] == ["client", "staff"] and mine[1]["sender_name"] not in ("", "Client")
    assert client.get("/api/portal/me", headers=me).json()["unread"]["agent"] == 0


def test_the_broker_conversation_is_private_from_the_agent(client, db):
    agent, cid, _, me = _portal(client, db)
    client.post("/api/portal/messages", headers=me, json={"channel": "broker", "body": "I'd like a different agent."})
    assert client.get("/api/messages/conversations", headers=agent).json() == []
    assert client.get(f"/api/messages/{cid}/broker", headers=agent).status_code == 404
    assert client.post(f"/api/messages/{cid}/broker", headers=agent, json={"body": "hi"}).status_code == 404
    assert client.get("/api/messages/unread-count", headers=agent).json() == 0
    broker = login(client, "broker@test.com")
    [conv] = client.get("/api/messages/conversations", headers=broker).json()
    assert conv["channel"] == "broker" and conv["unread"] == 1
    assert client.post(f"/api/messages/{cid}/broker", headers=broker, json={"body": "I'll call you today."}).status_code == 201


def test_other_agents_cant_read_the_thread(client, db):
    _, cid, _, me = _portal(client, db)
    client.post("/api/portal/messages", headers=me, json={"channel": "agent", "body": "hello"})
    other = login(client, "other@test.com")
    assert client.get(f"/api/messages/{cid}/agent", headers=other).status_code == 404
    assert client.get("/api/messages/conversations", headers=other).json() == []


def test_unassigned_clients_message_the_broker(client, db):
    make_user(db, "broker@test.com", UserRole.admin)
    broker = login(client, "broker@test.com")
    client.post("/api/public/intake", json={"first_name": "Dana", "last_name": "B", "email": "dana@example.com",
                                            "consent": True})
    cid = client.get("/api/admin/clients", headers=broker).json()[0]["client_id"]
    token = _token_from(client.post(f"/api/clients/{cid}/portal-invite", headers=broker).json()["invite_url"])
    me = {"Authorization": "Bearer " + client.post("/api/portal/accept", json={"token": token, "password": "client-pass-1"}).json()["access_token"]}
    o = client.get("/api/portal/me", headers=me).json()
    assert o["agent"] is None and "choosing the best agent" in o["stage_description"]
    r = client.post("/api/portal/messages", headers=me, json={"channel": "agent", "body": "hi"})
    assert r.status_code == 409
    assert client.post("/api/portal/messages", headers=me, json={"channel": "broker", "body": "hi"}).status_code == 201


def test_a_new_invite_resets_the_password(client, db):
    agent, cid, _, _ = _portal(client, db)
    token = _token_from(client.post(f"/api/clients/{cid}/portal-invite", headers=agent).json()["invite_url"])
    client.post("/api/portal/accept", json={"token": token, "password": "brand-new-pass"})
    assert client.post("/api/portal/login", json={"email": "aisha@example.com", "password": "brand-new-pass"}).status_code == 200
    assert client.post("/api/portal/login", json={"email": "aisha@example.com", "password": "client-pass-1"}).status_code == 401
