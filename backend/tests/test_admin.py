from app.models import Appointment, Client, Interaction, Lead
from app.models.enums import UserRole
from tests.conftest import at, login, make_property, make_user, new_client

FORM = {"first_name": "Dana", "last_name": "Brooks", "email": "dana@example.com", "client_type": "buyer",
        "budget_max": 400000, "preferred_city": "Chicago", "consent": True}


def _team(client, db):
    make_user(db, "broker@test.com", UserRole.admin)
    a = make_user(db, "a@test.com", UserRole.agent)
    b = make_user(db, "b@test.com", UserRole.agent)
    return login(client, "broker@test.com"), a, b


def test_broker_assigns_a_website_request_to_an_agent(client, db):
    broker, a, _ = _team(client, db)
    client.post("/api/public/intake", json=FORM)
    waiting = client.get("/api/admin/clients", headers=broker).json()
    assert len(waiting) == 1 and waiting[0]["from_website"] and waiting[0]["agent_id"] is None
    cid = waiting[0]["client_id"]
    r = client.post(f"/api/admin/clients/{cid}/assign", headers=broker, json={"agent_id": a.id})
    assert r.status_code == 200 and r.json()["agent_name"] == a.full_name
    assert client.get("/api/admin/clients", headers=broker).json() == []
    assert db.query(Lead).one().agent_id == a.id
    agent = login(client, "a@test.com")
    assert [x["id"] for x in client.get("/api/clients", headers=agent).json()] == [cid]
    assert "Assigned to" in db.query(Interaction).one().summary


def test_reassigning_moves_leads_and_upcoming_appointments(client, db):
    broker, a, b = _team(client, db)
    a_headers = login(client, "a@test.com")
    cid, lid = new_client(client, a_headers)
    p = make_property(db)
    client.post("/api/appointments", headers=a_headers, json={"client_id": cid, "property_id": p.id,
                "appointment_type": "viewing", "starts_at": at(3, 10), "ends_at": at(3, 11)})
    r = client.post(f"/api/admin/clients/{cid}/assign", headers=broker, json={"agent_id": b.id})
    assert r.status_code == 200 and r.json()["moved_appointments"] == 1
    assert db.get(Lead, lid).agent_id == b.id and db.query(Appointment).one().agent_id == b.id
    assert client.get(f"/api/clients/{cid}", headers=a_headers).status_code == 404
    assert "Moved from" in db.query(Interaction).order_by(Interaction.id.desc()).first().summary


def test_reassigning_is_refused_if_it_would_double_book_the_new_agent(client, db):
    broker, a, b = _team(client, db)
    a_headers, b_headers = login(client, "a@test.com"), login(client, "b@test.com")
    p = make_property(db)
    cid, _ = new_client(client, a_headers)
    other, _ = new_client(client, b_headers, email="other@example.com", first_name="Ben")
    slot = {"property_id": p.id, "appointment_type": "viewing", "starts_at": at(4, 10), "ends_at": at(4, 11)}
    client.post("/api/appointments", headers=a_headers, json={"client_id": cid, **slot})
    client.post("/api/appointments", headers=b_headers, json={"client_id": other, **slot})
    r = client.post(f"/api/admin/clients/{cid}/assign", headers=broker, json={"agent_id": b.id})
    assert r.status_code == 409 and "already has an appointment" in r.json()["detail"]
    assert db.get(Client, cid).agent_id == a.id


def test_unassigned_clients_cant_be_scheduled_yet(client, db):
    broker, _, _ = _team(client, db)
    client.post("/api/public/intake", json=FORM)
    cid = db.query(Client).one().id
    r = client.post("/api/appointments", headers=broker, json={"client_id": cid, "appointment_type": "meeting",
                    "starts_at": at(2, 10), "ends_at": at(2, 11)})
    assert r.status_code == 409 and "Assign this client" in r.json()["detail"]


def test_team_shows_each_persons_workload(client, db):
    broker, a, _ = _team(client, db)
    new_client(client, login(client, "a@test.com"))
    team = {m["email"]: m for m in client.get("/api/admin/team", headers=broker).json()}
    assert team["a@test.com"]["clients"] == 1 and team["a@test.com"]["open_leads"] == 1
    assert team["b@test.com"]["clients"] == 0


def test_broker_adds_a_new_broker_and_changes_roles(client, db):
    broker, a, _ = _team(client, db)
    r = client.post("/api/users", headers=broker, json={"email": "new.broker@test.com", "full_name": "New Broker",
                    "password": "long-enough-1", "role": "admin"})
    assert r.status_code == 201 and r.json()["role"] == "admin"
    r = client.patch(f"/api/users/{a.id}", headers=broker, json={"role": "admin", "full_name": "Agent Promoted"})
    assert r.status_code == 200 and r.json()["role"] == "admin" and r.json()["full_name"] == "Agent Promoted"


def test_a_deactivated_person_cant_sign_in(client, db):
    broker, a, _ = _team(client, db)
    assert client.patch(f"/api/users/{a.id}", headers=broker, json={"is_active": False}).json()["is_active"] is False
    r = client.post("/api/auth/login", data={"username": "a@test.com", "password": "password123"})
    assert r.status_code in (401, 403)
    client.patch(f"/api/users/{a.id}", headers=broker, json={"is_active": True})
    login(client, "a@test.com")


def test_brokers_cant_lock_themselves_out(client, db):
    broker, _, _ = _team(client, db)
    me = client.get("/api/auth/me", headers=broker).json()["id"]
    assert client.patch(f"/api/users/{me}", headers=broker, json={"is_active": False}).status_code == 409
    assert client.patch(f"/api/users/{me}", headers=broker, json={"role": "agent"}).status_code == 409
    # Another broker can deactivate them, though.
    make_user(db, "second@test.com", UserRole.admin)
    other = login(client, "second@test.com")
    assert client.patch(f"/api/users/{me}", headers=other, json={"is_active": False}).status_code == 200


def test_agents_cant_use_the_admin_area(client, db):
    _, a, b = _team(client, db)
    agent = login(client, "a@test.com")
    assert client.get("/api/admin/team", headers=agent).status_code == 403
    assert client.patch(f"/api/users/{b.id}", headers=agent, json={"is_active": False}).status_code == 403
