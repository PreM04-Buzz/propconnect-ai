# Data

Raw datasets are **not committed** (the property file is ~180 MB). Put them here locally:

```
data/raw/realtor-data.zip.csv                    # USA Real Estate Dataset (archive.zip also works)
data/raw/Metro_invt_fs_uc_sfrcondo_sm_month.csv  # Zillow metro for-sale inventory
```

Then, from `backend/` with the virtual environment active:

```
python -m app.scripts.prepare_data   # writes data/processed/properties.csv and market_inventory.csv
python -m app.scripts.load_data      # loads them into PostgreSQL
python -m app.scripts.seed_demo      # 2 demo agents, 40 clients, leads, interactions
```

Cleaning rules (from the Phase 1 profiling):
- Illinois listings with status `for_sale`; filter on completeness, **not** `prev_sold_date`
  (it is missing for about half of active listings).
- Price $50K–$5M, 1–8 beds, 1–8 baths, 400–10,000 sq ft; duplicates removed.
- ZIP codes stored as 5-character text (leading zeros kept).
- Street addresses are anonymized in the source, so fictional demo addresses are generated.
- Impossible sale dates (after 2026) are cleared.
- Zillow file reshaped from wide (one column per month) to one row per region per month.
