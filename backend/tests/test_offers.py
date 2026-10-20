from tests.conftest import make_property, new_client


def _offer(client, headers, cid, pid, amount=380000, submit=True):
    return client.post("/api/offers", headers=headers,
                       json={"client_id": cid, "property_id": pid, "amount": amount, "submit": submit})


def _status(client, headers, oid, **body):
    return client.post(f"/api/offers/{oid}/status", headers=headers, json=body)


def test_submitting_an_offer_moves_the_lead_to_negotiation(client, db, agent_headers):
    cid, lid = new_client(client, agent_headers)
    p = make_property(db, price=395000)
    r = _offer(client, agent_headers, cid, p.id)
    assert r.status_code == 201 and r.json()["status"] == "submitted" and r.json()["list_price"] == 395000
    lead = client.get(f"/api/leads/{lid}", headers=agent_headers).json()
    assert lead["stage"] == "negotiation" and lead["history"][-1]["to_stage"] == "negotiation"


def test_draft_offers_dont_move_the_pipeline(client, db, agent_headers):
    cid, lid = new_client(client, agent_headers)
    p = make_property(db)
    oid = _offer(client, agent_headers, cid, p.id, submit=False).json()["id"]
    assert client.get(f"/api/leads/{lid}", headers=agent_headers).json()["stage"] == "new"
    assert _status(client, agent_headers, oid, status="submitted", amount=375000).json()["amount"] == 375000
    assert client.get(f"/api/leads/{lid}", headers=agent_headers).json()["stage"] == "negotiation"


def test_counter_needs_an_amount(client, db, agent_headers):
    cid, _ = new_client(client, agent_headers)
    oid = _offer(client, agent_headers, cid, make_property(db).id).json()["id"]
    assert _status(client, agent_headers, oid, status="countered").status_code == 422
    r = _status(client, agent_headers, oid, status="countered", counter_amount=392000)
    assert r.status_code == 200 and r.json()["counter_amount"] == 392000


def test_accepting_wins_the_lead_and_sells_the_property(client, db, agent_headers):
    cid, lid = new_client(client, agent_headers)
    p = make_property(db)
    oid = _offer(client, agent_headers, cid, p.id).json()["id"]
    r = _status(client, agent_headers, oid, status="accepted")
    assert r.status_code == 200 and r.json()["lead_stage"] == "won" and r.json()["decided_at"]
    assert client.get(f"/api/properties/{p.id}", headers=agent_headers).json()["status"] == "sold"
    # the property is off the market now
    other, _ = new_client(client, agent_headers, email="b@example.com", first_name="Ben")
    assert _offer(client, agent_headers, other, p.id).status_code == 409


def test_only_one_accepted_offer_per_property(client, db, agent_headers):
    p = make_property(db)
    c1, _ = new_client(client, agent_headers)
    c2, _ = new_client(client, agent_headers, first_name="Ben", email="ben@example.com")
    o1 = _offer(client, agent_headers, c1, p.id).json()["id"]
    o2 = _offer(client, agent_headers, c2, p.id, amount=385000).json()["id"]
    assert _status(client, agent_headers, o1, status="accepted").status_code == 200
    assert _status(client, agent_headers, o2, status="accepted").status_code == 409


def test_final_offers_cant_change(client, db, agent_headers):
    cid, _ = new_client(client, agent_headers)
    oid = _offer(client, agent_headers, cid, make_property(db).id).json()["id"]
    assert _status(client, agent_headers, oid, status="rejected").status_code == 200
    assert _status(client, agent_headers, oid, status="accepted").status_code == 409


def test_offers_list_filters(client, db, agent_headers):
    cid, lid = new_client(client, agent_headers)
    p1, p2 = make_property(db), make_property(db, street_address="9 Elm St")
    _offer(client, agent_headers, cid, p1.id)
    o2 = _offer(client, agent_headers, cid, p2.id).json()["id"]
    _status(client, agent_headers, o2, status="withdrawn")
    assert len(client.get("/api/offers", headers=agent_headers, params={"status": "submitted"}).json()) == 1
    assert len(client.get("/api/offers", headers=agent_headers, params={"lead_id": lid}).json()) == 2
