from app.core.config import get_settings
from app.services import ai_assistant
from tests.conftest import BUYER, make_property


def _setup(client, db, headers, interest=True):
    cid = client.post("/api/clients", json=BUYER, headers=headers).json()["id"]
    p = make_property(db, price=375000, street_address="48 Maple Ave")
    if interest:
        client.post(f"/api/clients/{cid}/interests", json={"property_id": p.id, "interest_level": "high"}, headers=headers)
    lid = client.get(f"/api/clients/{cid}", headers=headers).json()["leads"][0]["id"]
    client.post(f"/api/leads/{lid}/move", json={"to_stage": "qualified"}, headers=headers)
    return cid, lid


def test_without_api_key_uses_rule_based_fallback(client, db, agent_headers):
    _, lid = _setup(client, db, agent_headers)
    r = client.post(f"/api/leads/{lid}/ai/next-step", headers=agent_headers)
    assert r.status_code == 201, r.text
    s = r.json()
    assert s["source"] == "rules" and s["action_type"] == "schedule_viewing"
    assert "48 Maple Ave" in s["recommended_action"]


def test_no_interests_suggests_matching_listings(client, db, agent_headers):
    _, lid = _setup(client, db, agent_headers, interest=False)
    s = client.post(f"/api/leads/{lid}/ai/next-step", headers=agent_headers).json()
    assert s["action_type"] == "send_listings" and "48 Maple Ave" in s["recommended_action"]


def test_openai_response_is_used_when_valid(client, db, agent_headers, monkeypatch):
    _, lid = _setup(client, db, agent_headers)
    seen = {}

    def fake(ctx):
        seen.update(ctx)
        return {"intent_level": "high", "summary": "Ready buyer.", "recommended_action": "Book a viewing.",
                "action_type": "schedule_viewing", "reasoning": "Pre-approved.", "draft_message": "Hi Aisha!"}

    monkeypatch.setattr(get_settings(), "openai_api_key", "test-key")
    monkeypatch.setattr(ai_assistant, "_call_openai", fake)
    s = client.post(f"/api/leads/{lid}/ai/next-step", headers=agent_headers).json()
    assert s["source"] == "openai" and s["summary"] == "Ready buyer."
    # the model only receives facts from the database
    assert seen["client"]["budget_max"] == "$400,000"
    assert seen["properties_of_interest"][0]["address"] == "48 Maple Ave, Naperville"


def test_invalid_model_output_falls_back(client, db, agent_headers, monkeypatch):
    _, lid = _setup(client, db, agent_headers)
    monkeypatch.setattr(get_settings(), "openai_api_key", "test-key")
    monkeypatch.setattr(ai_assistant, "_call_openai", lambda ctx: {"intent_level": "very high"})
    s = client.post(f"/api/leads/{lid}/ai/next-step", headers=agent_headers).json()
    assert s["source"] == "rules"


def test_accept_logs_interaction_and_cannot_decide_twice(client, db, agent_headers):
    cid, lid = _setup(client, db, agent_headers)
    sid = client.post(f"/api/leads/{lid}/ai/next-step", headers=agent_headers).json()["id"]
    r = client.post(f"/api/ai/suggestions/{sid}/decision",
                    json={"status": "accepted", "draft_message": "Edited by agent"}, headers=agent_headers)
    assert r.status_code == 200 and r.json()["status"] == "accepted"
    timeline = client.get(f"/api/clients/{cid}", headers=agent_headers).json()["interactions"]
    assert "Edited by agent" in timeline[0]["summary"]
    again = client.post(f"/api/ai/suggestions/{sid}/decision", json={"status": "dismissed"}, headers=agent_headers)
    assert again.status_code == 409
    history = client.get(f"/api/leads/{lid}/ai/suggestions", headers=agent_headers).json()
    assert len(history) == 1
