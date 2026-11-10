from app.models import Client, Lead
from app.models.enums import UserRole
from tests.conftest import login, make_user

FORM = {"first_name": "Dana", "last_name": "Brooks", "email": "Dana@Example.com", "phone": "312-555-0101",
        "client_type": "buyer", "preferred_city": "Chicago", "budget_min": 250000, "budget_max": 400000,
        "min_bedrooms": 2, "min_bathrooms": 1, "financing_status": "pre_approved", "purchase_timeline_months": 3,
        "notes": "Close to the Blue Line please", "consent": True}


def test_a_client_can_send_their_details_without_signing_in(client, db):
    r = client.post("/api/public/intake", json=FORM)
    assert r.status_code == 202 and "agent will get in touch" in r.json()["message"]
    c = db.query(Client).one()
    assert c.agent_id is None and c.email == "dana@example.com" and c.consent_at is not None
    assert c.budget_confirmed is False and "Blue Line" in c.notes
    lead = db.query(Lead).one()
    assert lead.agent_id is None and lead.source == "Website form" and lead.stage.value == "new"
    assert lead.score is not None  # scored straight away, like any other lead


def test_consent_is_required(client, db):
    r = client.post("/api/public/intake", json={**FORM, "consent": False})
    assert r.status_code == 422 and db.query(Client).count() == 0


def test_budget_must_make_sense(client):
    assert client.post("/api/public/intake", json={**FORM, "budget_min": 500000}).status_code == 422


def test_bots_that_fill_the_hidden_field_get_a_polite_reply_and_nothing_is_saved(client, db):
    r = client.post("/api/public/intake", json={**FORM, "website": "http://spam.example"})
    assert r.status_code == 202 and db.query(Client).count() == 0


def test_sending_the_form_twice_adds_a_note_not_a_duplicate(client, db):
    client.post("/api/public/intake", json=FORM)
    r = client.post("/api/public/intake", json={**FORM, "email": "dana@example.com", "notes": "Now open to Evanston"})
    assert r.status_code == 202 and db.query(Client).count() == 1
    assert "Evanston" in db.query(Client).one().notes


def test_one_address_is_limited_to_five_requests_an_hour(client):
    for i in range(5):
        assert client.post("/api/public/intake", json={**FORM, "email": f"p{i}@example.com"}).status_code == 202
    assert client.post("/api/public/intake", json={**FORM, "email": "p9@example.com"}).status_code == 429


def test_agents_never_see_unassigned_requests_but_the_broker_does(client, db):
    client.post("/api/public/intake", json=FORM)
    make_user(db, "agent@test.com", UserRole.agent)
    make_user(db, "broker@test.com", UserRole.admin)
    cid = db.query(Client).one().id
    agent = login(client, "agent@test.com")
    assert client.get("/api/clients", headers=agent).json() == []
    assert client.get(f"/api/clients/{cid}", headers=agent).status_code == 404
    broker = login(client, "broker@test.com")
    assert [x["id"] for x in client.get("/api/clients", headers=broker).json()] == [cid]
