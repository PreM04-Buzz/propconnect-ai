from tests.conftest import at, make_property, new_client


def _viewing(client, headers, cid, pid, start, end):
    return client.post("/api/appointments", headers=headers, json={
        "client_id": cid, "property_id": pid, "appointment_type": "viewing", "starts_at": start, "ends_at": end})


def test_schedule_and_list_a_viewing(client, db, agent_headers):
    cid, _ = new_client(client, agent_headers)
    p = make_property(db)
    r = _viewing(client, agent_headers, cid, p.id, at(2, 10), at(2, 11))
    assert r.status_code == 201, r.text
    assert r.json()["client_name"] == "Aisha Patel" and r.json()["property_address"] == "12 Oak St, Naperville"
    week = client.get("/api/appointments", headers=agent_headers,
                      params={"start": at(0, 0), "end": at(7, 0)}).json()
    assert [a["id"] for a in week] == [r.json()["id"]]


def test_double_booking_is_blocked(client, db, agent_headers):
    cid, _ = new_client(client, agent_headers)
    p = make_property(db)
    assert _viewing(client, agent_headers, cid, p.id, at(2, 10), at(2, 11)).status_code == 201
    clash = _viewing(client, agent_headers, cid, p.id, at(2, 10, 30), at(2, 11, 30))
    assert clash.status_code == 409 and "overlaps" in clash.json()["detail"]
    # back to back is fine
    assert _viewing(client, agent_headers, cid, p.id, at(2, 11), at(2, 12)).status_code == 201


def test_cancelled_appointments_free_the_slot(client, db, agent_headers):
    cid, _ = new_client(client, agent_headers)
    p = make_property(db)
    aid = _viewing(client, agent_headers, cid, p.id, at(3, 9), at(3, 10)).json()["id"]
    client.post(f"/api/appointments/{aid}/status", headers=agent_headers, json={"status": "cancelled"})
    assert _viewing(client, agent_headers, cid, p.id, at(3, 9), at(3, 10)).status_code == 201


def test_rescheduling_checks_for_clashes(client, db, agent_headers):
    cid, _ = new_client(client, agent_headers)
    p = make_property(db)
    _viewing(client, agent_headers, cid, p.id, at(4, 9), at(4, 10))
    second = _viewing(client, agent_headers, cid, p.id, at(4, 14), at(4, 15)).json()["id"]
    r = client.patch(f"/api/appointments/{second}", headers=agent_headers,
                     json={"starts_at": at(4, 9, 30), "ends_at": at(4, 10, 30)})
    assert r.status_code == 409
    r = client.patch(f"/api/appointments/{second}", headers=agent_headers,
                     json={"starts_at": at(4, 16), "ends_at": at(4, 17), "notes": "Moved to the afternoon"})
    assert r.status_code == 200 and r.json()["notes"] == "Moved to the afternoon"


def test_bad_times_and_missing_property_are_rejected(client, db, agent_headers):
    cid, _ = new_client(client, agent_headers)
    p = make_property(db)
    assert _viewing(client, agent_headers, cid, p.id, at(2, 11), at(2, 10)).status_code == 422
    assert _viewing(client, agent_headers, cid, None, at(2, 10), at(2, 11)).status_code == 422


def test_viewings_count_in_the_score_and_completing_needs_feedback(client, db, agent_headers):
    cid, lid = new_client(client, agent_headers)
    p = make_property(db)
    before = client.get(f"/api/leads/{lid}", headers=agent_headers).json()["score"]
    aid = _viewing(client, agent_headers, cid, p.id, at(-1, 10), at(-1, 11)).json()["id"]
    r = client.post(f"/api/appointments/{aid}/status", headers=agent_headers, json={"status": "completed"})
    assert r.status_code == 422
    r = client.post(f"/api/appointments/{aid}/status", headers=agent_headers,
                    json={"status": "completed", "outcome": "Loved the kitchen"})
    assert r.status_code == 200 and r.json()["outcome"] == "Loved the kitchen"
    assert client.get(f"/api/leads/{lid}", headers=agent_headers).json()["score"] == before + 10
    again = client.post(f"/api/appointments/{aid}/status", headers=agent_headers, json={"status": "cancelled"})
    assert again.status_code == 409
