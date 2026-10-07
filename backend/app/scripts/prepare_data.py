"""Clean the raw datasets into load-ready CSVs.

Run from backend/ (needs pandas, included in requirements-dev.txt):
    python -m app.scripts.prepare_data
    python -m app.scripts.prepare_data --state Illinois --sample 800

Input  (git-ignored):  data/raw/realtor-data.zip.csv  (or the original archive.zip)
                       data/raw/Metro_invt_fs_uc_sfrcondo_sm_month.csv
Output (git-ignored):  data/processed/properties.csv
                       data/processed/market_inventory.csv
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
RAW, OUT = ROOT / "data" / "raw", ROOT / "data" / "processed"

STREETS = ["Oak", "Maple", "Cedar", "Pine", "Elm", "Washington", "Lincoln", "Lake", "Hill", "Park", "Prairie",
           "Ridge", "Meadow", "Willow", "Sunset", "Highland", "Forest", "River", "Spring", "Chestnut", "Walnut",
           "Birch", "Jefferson", "Madison", "Jackson", "Franklin", "Grove", "Church", "Center", "Main"]
SUFFIXES = ["St", "Ave", "Dr", "Ln", "Ct", "Rd", "Way", "Blvd", "Pl"]


def find_realtor() -> Path:
    for name in ("realtor-data.zip.csv", "realtor-data.csv", "archive.zip"):
        if (RAW / name).exists():
            return RAW / name
    raise SystemExit(f"Put realtor-data.zip.csv (or archive.zip) in {RAW}")


def prepare_properties(state: str, sample: int, seed: int) -> pd.DataFrame:
    path = find_realtor()
    print(f"Reading {path.name} ...")
    df = pd.read_csv(path, dtype={"zip_code": "string", "street": "string", "brokered_by": "string"})
    print(f"  {len(df):,} rows")
    df = df[(df["state"] == state) & (df["status"] == "for_sale")]
    # Filter on status and completeness, not prev_sold_date: it is missing for ~51% of active listings.
    df = df.dropna(subset=["price", "bed", "bath", "house_size", "city", "zip_code"])
    df = df[df["price"].between(50_000, 5_000_000) & df["bed"].between(1, 8) & df["bath"].between(1, 8)
            & df["house_size"].between(400, 10_000)]
    df = df.drop_duplicates(subset=["street", "city", "zip_code", "price"])
    print(f"  {len(df):,} complete {state} listings for sale")

    # ZIP: stored as text, zero-padded (the CSV loses leading zeros).
    df["zip_code"] = df["zip_code"].str.replace(r"\.0$", "", regex=True).str.zfill(5).str[:5]
    df = df.sample(n=min(sample, len(df)), random_state=seed).reset_index(drop=True)

    # The dataset anonymizes street addresses, so demo addresses are generated (fictional).
    rng = np.random.default_rng(seed)
    df["street_address"] = [
        f"{rng.integers(10, 9999)} {rng.choice(STREETS)} {rng.choice(SUFFIXES)}" for _ in range(len(df))
    ]
    out = pd.DataFrame({
        "source_ref": "realtor:" + df["street"].fillna("na").astype(str).str.replace(r"\.0$", "", regex=True),
        "status": "for_sale",
        "price": df["price"].round(0),
        "bedrooms": df["bed"].astype(int),
        "bathrooms": df["bath"].astype(float),
        "house_size_sqft": df["house_size"].astype(int),
        "acre_lot": df["acre_lot"].round(3),
        "street_address": df["street_address"],
        "city": df["city"].str.strip(),
        "state": df["state"],
        "zip_code": df["zip_code"],
        "prev_sold_date": pd.to_datetime(df["prev_sold_date"], errors="coerce").dt.date,
    })
    # Impossible dates (e.g. year 3019) become empty.
    bad = out["prev_sold_date"].apply(lambda d: d is not None and not pd.isna(d) and d.year > 2026)
    out.loc[bad, "prev_sold_date"] = None
    return out


def prepare_market() -> pd.DataFrame:
    path = RAW / "Metro_invt_fs_uc_sfrcondo_sm_month.csv"
    if not path.exists():
        raise SystemExit(f"Put Metro_invt_fs_uc_sfrcondo_sm_month.csv in {RAW}")
    wide = pd.read_csv(path)
    id_cols = ["RegionID", "SizeRank", "RegionName", "RegionType", "StateName"]
    long = wide.melt(id_vars=id_cols, var_name="month", value_name="inventory")
    long = long.rename(columns={"RegionID": "region_id", "SizeRank": "size_rank", "RegionName": "region_name",
                                "RegionType": "region_type", "StateName": "state_name"})
    long["month"] = pd.to_datetime(long["month"]).dt.date
    long["inventory"] = long["inventory"].round().astype("Int64")
    return long[["region_id", "region_name", "region_type", "state_name", "size_rank", "month", "inventory"]]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", default="Illinois")
    ap.add_argument("--sample", type=int, default=800)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    props = prepare_properties(args.state, args.sample, args.seed)
    props.to_csv(OUT / "properties.csv", index=False)
    print(f"Wrote {len(props):,} properties -> data/processed/properties.csv")
    print("  Top cities:", ", ".join(f"{c} ({n})" for c, n in props["city"].value_counts().head(6).items()))

    market = prepare_market()
    market.to_csv(OUT / "market_inventory.csv", index=False)
    print(f"Wrote {len(market):,} market rows ({market['region_id'].nunique()} regions) -> data/processed/market_inventory.csv")


if __name__ == "__main__":
    main()
