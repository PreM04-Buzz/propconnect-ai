"""Direct tests for endpoints that were only exercised indirectly before."""
from tests.conftest import make_property, new_client


def test_ai_status_reports_no_key(client, agent_headers):
    assert client.get("/api/ai/status", headers=agent_headers).json() == {"ai_enabled": False, "model": None}


def test_remove_from_shortlist(client, db, agent_headers):
    cid, _ = new_client(client, agent_headers)
    p = make_property(db)
    iid = client.post(f"/api/clients/{cid}/interests", headers=agent_headers, json={"property_id": p.id}).json()["id"]
    assert client.delete(f"/api/clients/{cid}/interests/{iid}", headers=agent_headers).status_code == 204
    assert client.get(f"/api/clients/{cid}", headers=agent_headers).json()["interests"] == []


def test_open_a_second_lead_and_edit_it(client, agent_headers):
    cid, _ = new_client(client, agent_headers)
    r = client.post("/api/leads", headers=agent_headers, json={"client_id": cid, "source": "Referral"})
    assert r.status_code == 201 and r.json()["history"][0]["to_stage"] == "new"
    lid = r.json()["id"]
    assert client.patch(f"/api/leads/{lid}", headers=agent_headers, json={"source": "Open house"}).json()["source"] == "Open house"
    assert client.get(f"/api/leads/{lid}", headers=agent_headers).json()["client"]["id"] == cid


def test_read_and_update_a_listing(client, db, agent_headers):
    p = make_property(db)
    assert client.get(f"/api/properties/{p.id}", headers=agent_headers).json()["city"] == "Naperville"
    r = client.patch(f"/api/properties/{p.id}", headers=agent_headers, json={"price": 340000})
    assert r.status_code == 200 and r.json()["price"] == 340000
    assert client.get("/api/properties/999999", headers=agent_headers).status_code == 404
