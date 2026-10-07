from tests.conftest import BUYER


def _lead(client, headers):
    return client.post("/api/clients", json=BUYER, headers=headers).json()["leads"][0]["id"]


def test_move_records_history(client, agent_headers):
    lid = _lead(client, agent_headers)
    for stage in ("contacted", "qualified"):
        r = client.post(f"/api/leads/{lid}/move", json={"to_stage": stage}, headers=agent_headers)
        assert r.status_code == 200
    body = r.json()
    assert body["stage"] == "qualified"
    assert [(h["from_stage"], h["to_stage"]) for h in body["history"]] == [
        (None, "new"), ("new", "contacted"), ("contacted", "qualified")]
    assert len(body["score_breakdown"]) == 6


def test_lost_needs_a_reason(client, agent_headers):
    lid = _lead(client, agent_headers)
    assert client.post(f"/api/leads/{lid}/move", json={"to_stage": "lost"}, headers=agent_headers).status_code == 422
    r = client.post(f"/api/leads/{lid}/move", json={"to_stage": "lost", "lost_reason": "Bought elsewhere"},
                    headers=agent_headers)
    assert r.json()["lost_reason"] == "Bought elsewhere"


def test_board_and_summary(client, agent_headers):
    lid = _lead(client, agent_headers)
    client.post(f"/api/leads/{lid}/move", json={"to_stage": "proposal"}, headers=agent_headers)
    cards = client.get("/api/leads", headers=agent_headers).json()
    assert cards[0]["client_name"] == "Aisha Patel" and cards[0]["stage"] == "proposal"
    summary = {s["stage"]: s["count"] for s in client.get("/api/leads/summary", headers=agent_headers).json()}
    assert summary["proposal"] == 1 and summary["new"] == 0 and len(summary) == 7
