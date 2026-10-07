"""Load the cleaned CSVs into the database.

Run from backend/ after prepare_data:
    python -m app.scripts.load_data            # loads properties (if empty) and market data
    python -m app.scripts.load_data --replace  # wipes listings and everything linked to them first
"""
import argparse
import csv
from datetime import date
from pathlib import Path

from sqlalchemy import delete, func, insert, select

from app.db.session import SessionLocal
from app.models import Appointment, MarketInventory, Offer, Property, PropertyInterest

ROOT = Path(__file__).resolve().parents[3]
PROCESSED = ROOT / "data" / "processed"


def _num(v, cast=float):
    return cast(float(v)) if v not in ("", None) else None


def _date(v):
    return date.fromisoformat(v) if v else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--replace", action="store_true", help="delete existing listings first")
    args = ap.parse_args()

    with SessionLocal() as db:
        existing = db.scalar(select(func.count(Property.id))) or 0
        if existing and not args.replace:
            print(f"{existing} properties already loaded; skipping (use --replace to reload).")
        else:
            if args.replace:
                for model in (Offer, Appointment, PropertyInterest, Property):
                    db.execute(delete(model))
            with open(PROCESSED / "properties.csv", newline="", encoding="utf-8") as f:
                rows = [{
                    "source_ref": r["source_ref"], "status": r["status"], "price": _num(r["price"]),
                    "bedrooms": _num(r["bedrooms"], int), "bathrooms": _num(r["bathrooms"]),
                    "house_size_sqft": _num(r["house_size_sqft"], int), "acre_lot": _num(r["acre_lot"]),
                    "street_address": r["street_address"], "city": r["city"], "state": r["state"],
                    "zip_code": r["zip_code"].zfill(5), "prev_sold_date": _date(r["prev_sold_date"]),
                } for r in csv.DictReader(f)]
            db.execute(insert(Property), rows)
            print(f"Loaded {len(rows)} properties.")

        db.execute(delete(MarketInventory))
        with open(PROCESSED / "market_inventory.csv", newline="", encoding="utf-8") as f:
            batch, total = [], 0
            for r in csv.DictReader(f):
                batch.append({"region_id": int(r["region_id"]), "region_name": r["region_name"],
                              "region_type": r["region_type"], "state_name": r["state_name"] or None,
                              "size_rank": int(r["size_rank"]), "month": _date(r["month"]),
                              "inventory": _num(r["inventory"], int)})
                if len(batch) == 5000:
                    db.execute(insert(MarketInventory), batch)
                    total += len(batch)
                    batch = []
            if batch:
                db.execute(insert(MarketInventory), batch)
                total += len(batch)
        db.commit()
        print(f"Loaded {total} market inventory rows.")


if __name__ == "__main__":
    main()
