from datetime import date

from app.models import MarketInventory
from app.models.enums import UserRole
from tests.conftest import login, make_property, make_user, new_client


def _month_end(y, m):
    return date(y + (m == 12), m % 12 + 1, 1).fromordinal(date(y + (m == 12), m % 12 + 1, 1).toordinal() - 1)


def _load(db):
    """Two small metros: Chicago (halves since 2019) and Springfield (flat), plus the US."""
    rows = []
    for y in range(2019, 2027):
        for m in range(1, 13):
            if (y, m) > (2026, 8):
                break
            k = (y - 2019) * 12 + m
            rows += [
                MarketInventory(region_id=1, region_name="Chicago, IL", region_type="msa", state_name="IL", size_rank=3,
                                month=_month_end(y, m), inventory=40000 - k * 200),
                MarketInventory(region_id=2, region_name="Springfield, IL", region_type="msa", state_name="IL",
                                size_rank=200, month=_month_end(y, m), inventory=1000),
                MarketInventory(region_id=9, region_name="United States", region_type="country", state_name=None,
                                size_rank=0, month=_month_end(y, m), inventory=1_000_000 + k * 1000),
                MarketInventory(region_id=7, region_name="St. Louis, MO", region_type="msa", state_name="MO",
                                size_rank=20, month=_month_end(y, m), inventory=8000),
            ]
    db.add_all(rows)
    db.commit()


def test_regions_default_to_illinois_and_the_us_and_can_be_searched(client, db, agent_headers):
    _load(db)
    names = [r["region_name"] for r in client.get("/api/market/regions", headers=agent_headers).json()]
    assert names == ["United States", "Chicago, IL", "Springfield, IL"]   # largest first, no St. Louis
    found = client.get("/api/market/regions", headers=agent_headers, params={"q": "louis"}).json()
    assert [r["region_name"] for r in found] == ["St. Louis, MO"] and found[0]["latest_inventory"] == 8000


def test_trend_statistics_are_right(client, db, agent_headers):
    _load(db)
    [chi] = client.get("/api/market/trends", headers=agent_headers, params={"region_id": 1}).json()
    s = chi["stats"]
    assert len(chi["points"]) == 92 and s["latest"] == 40000 - 92 * 200 == 21600
    assert s["latest_month"] == "2026-08-31"
    assert s["change_1y_pct"] == round((21600 - 24000) / 24000 * 100, 1)       # -10.0
    assert s["change_vs_2019_pct"] == round((21600 - 38700) / 38700 * 100, 1)  # 2019 average was 38,700
    assert s["trend_3m"] == "falling" and s["peak"] == 39800 and s["low"] == 21600
    assert "well below the 2019 level" in s["summary"] and "21,600" in s["summary"]
    [spr] = client.get("/api/market/trends", headers=agent_headers, params={"region_id": 2}).json()
    assert spr["stats"]["trend_3m"] == "steady" and "close to the 2019 level" in spr["stats"]["summary"]


def test_compare_up_to_three_areas(client, db, agent_headers):
    _load(db)
    r = client.get("/api/market/trends", headers=agent_headers, params={"region_id": [1, 2, 9]})
    assert [s["region_name"] for s in r.json()] == ["Chicago, IL", "Springfield, IL", "United States"]
    too_many = client.get("/api/market/trends", headers=agent_headers, params={"region_id": [1, 2, 9, 7]})
    assert too_many.status_code == 422
    assert client.get("/api/market/trends", headers=agent_headers, params={"region_id": 555}).status_code == 404


def test_my_areas_match_cities_suburbs_and_admit_gaps(client, db):
    _load(db)
    make_user(db, "agent@test.com", UserRole.agent)
    make_user(db, "other@test.com", UserRole.agent)
    make_user(db, "broker@test.com", UserRole.admin)
    agent, other = login(client, "agent@test.com"), login(client, "other@test.com")
    make_property(db, city="Naperville", zip_code="60540")
    make_property(db, city="Belleville", zip_code="62220")
    for i, city in enumerate(["Chicago", "Chicago", "Naperville", "Belleville"]):
        new_client(client, agent, email=f"c{i}@example.com", preferred_city=city, preferred_state="Illinois")
    new_client(client, other, email="o@example.com", preferred_city="Springfield", preferred_state="Illinois")

    areas = {a["city"]: a for a in client.get("/api/market/my-areas", headers=agent).json()}
    assert set(areas) == {"Chicago", "Naperville", "Belleville"}                # only this agent's clients
    assert areas["Chicago"]["clients"] == 2 and areas["Chicago"]["match"] == "city"
    assert areas["Naperville"]["region_name"] == "Chicago, IL" and areas["Naperville"]["match"] == "chicago_area"
    assert areas["Belleville"]["region_id"] is None                             # no guessing
    assert areas["Chicago"]["latest"] == 21600 and areas["Chicago"]["trend_3m"] == "falling"
    broker = {a["city"] for a in client.get("/api/market/my-areas", headers=login(client, "broker@test.com")).json()}
    assert "Springfield" in broker and "Chicago" in broker                     # brokers see every client's area


def test_market_needs_sign_in(client, db):
    assert client.get("/api/market/regions").status_code == 401
