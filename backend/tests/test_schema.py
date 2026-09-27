from sqlalchemy import inspect

from app.db.base import Base
import app.models  # noqa: F401  (registers every table)

EXPECTED = {
    "users", "clients", "leads", "lead_stage_history", "properties",
    "property_interests", "interactions", "appointments", "offers", "market_inventory",
}


def test_all_tables_registered():
    assert EXPECTED <= set(Base.metadata.tables)


def test_tables_create(db):
    assert EXPECTED <= set(inspect(db.get_bind()).get_table_names())
