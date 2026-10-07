from tests.conftest import make_property


def test_filters_and_paging(client, db, agent_headers):
    make_property(db, price=250000, bedrooms=2, city="Joliet", zip_code="60431")
    make_property(db, price=450000, bedrooms=3)
    make_property(db, price=650000, bedrooms=4)
    r = client.get("/api/properties?min_price=300000&max_price=700000&min_beds=3", headers=agent_headers).json()
    assert r["total"] == 2 and [p["price"] for p in r["items"]] == [450000, 650000]
    r = client.get("/api/properties?city=joliet", headers=agent_headers).json()
    assert r["total"] == 1
    r = client.get("/api/properties?page_size=1&page=2&sort=price_desc", headers=agent_headers).json()
    assert r["items"][0]["price"] == 450000


def test_cities_list(client, db, agent_headers):
    make_property(db)
    make_property(db, street_address="2 Main St")
    assert client.get("/api/properties/cities", headers=agent_headers).json() == [{"city": "Naperville", "count": 2}]


def test_create_validates_zip(client, agent_headers):
    body = {"price": 300000, "city": "Aurora", "state": "Illinois", "zip_code": "605"}
    assert client.post("/api/properties", json=body, headers=agent_headers).status_code == 422
    body["zip_code"] = "60505"
    r = client.post("/api/properties", json=body, headers=agent_headers)
    assert r.status_code == 201 and r.json()["zip_code"] == "60505"


def test_only_brokers_delete_listings(client, db, agent_headers, admin_headers):
    p = make_property(db)
    assert client.delete(f"/api/properties/{p.id}", headers=agent_headers).status_code == 403
    assert client.delete(f"/api/properties/{p.id}", headers=admin_headers).status_code == 204
