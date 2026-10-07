from app.models.enums import UserRole
from tests.conftest import BUYER, login, make_property, make_user


def test_create_client_also_opens_a_lead(client, agent_headers):
    r = client.post("/api/clients", json=BUYER, headers=agent_headers)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["first_name"] == "Aisha"
    assert len(body["leads"]) == 1 and body["leads"][0]["stage"] == "new"
    # pre-approved (20) + 2-month timeline (20) + confirmed budget (15) = 55
    assert body["leads"][0]["score"] == 55 and body["leads"][0]["priority"] == "medium"


def test_budget_min_cannot_exceed_max(client, agent_headers):
    r = client.post("/api/clients", json={**BUYER, "budget_min": 500000}, headers=agent_headers)
    assert r.status_code == 422


def test_search_and_update(client, agent_headers):
    cid = client.post("/api/clients", json=BUYER, headers=agent_headers).json()["id"]
    assert len(client.get("/api/clients?q=aisha", headers=agent_headers).json()) == 1
    assert client.get("/api/clients?q=nobody", headers=agent_headers).json() == []
    r = client.patch(f"/api/clients/{cid}", json={"phone": "555-0100"}, headers=agent_headers)
    assert r.status_code == 200 and r.json()["phone"] == "555-0100"


def test_agents_only_see_their_own_clients(client, db, agent_headers):
    cid = client.post("/api/clients", json=BUYER, headers=agent_headers).json()["id"]
    make_user(db, "other@test.com", UserRole.agent)
    other = login(client, "other@test.com")
    assert client.get("/api/clients", headers=other).json() == []
    assert client.get(f"/api/clients/{cid}", headers=other).status_code == 404


def test_broker_sees_all_clients(client, agent_headers, admin_headers):
    client.post("/api/clients", json=BUYER, headers=agent_headers)
    assert len(client.get("/api/clients", headers=admin_headers).json()) == 1


def test_interactions_and_interests_raise_the_score(client, db, agent_headers):
    cid = client.post("/api/clients", json=BUYER, headers=agent_headers).json()["id"]
    p = make_property(db)
    r = client.post(f"/api/clients/{cid}/interactions", json={"interaction_type": "call", "summary": "Intro call"},
                    headers=agent_headers)
    assert r.status_code == 201
    r = client.post(f"/api/clients/{cid}/interests", json={"property_id": p.id, "interest_level": "high"},
                    headers=agent_headers)
    assert r.status_code == 201 and r.json()["property"]["city"] == "Naperville"
    detail = client.get(f"/api/clients/{cid}", headers=agent_headers).json()
    assert len(detail["interactions"]) == 1 and len(detail["interests"]) == 1
    assert detail["leads"][0]["score"] == 55 + 15 + 10


def test_matches_rank_the_best_fit_first(client, db, agent_headers):
    cid = client.post("/api/clients", json=BUYER, headers=agent_headers).json()["id"]
    make_property(db, price=390000, city="Naperville")
    make_property(db, price=395000, city="Joliet", street_address="9 Elm St", zip_code="60431")
    matches = client.get(f"/api/clients/{cid}/matches", headers=agent_headers).json()
    assert matches[0]["property"]["city"] == "Naperville" and matches[0]["score"] == 100
    assert matches[0]["score"] > matches[1]["score"]


def test_delete_client_removes_their_lead(client, agent_headers):
    cid = client.post("/api/clients", json=BUYER, headers=agent_headers).json()["id"]
    assert client.delete(f"/api/clients/{cid}", headers=agent_headers).status_code == 204
    assert client.get("/api/leads", headers=agent_headers).json() == []
