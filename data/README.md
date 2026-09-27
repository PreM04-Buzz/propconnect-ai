# Data

Raw datasets are **not committed** (the property file is ~180 MB). Put them here locally:

```
data/raw/realtor-data.zip.csv                    # USA Real Estate Dataset (from archive.zip)
data/raw/Metro_invt_fs_uc_sfrcondo_sm_month.csv  # Zillow metro for-sale inventory
```

Both `data/raw/` and `data/processed/` are git-ignored. Cleaning and loading scripts
arrive in Phase 2; they will write load-ready files to `data/processed/`.

Known issues to handle in Phase 2 (from the initial profiling):
- `prev_sold_date` is missing for about half of `for_sale` rows, so don't filter active listings by it.
- `zip_code` must be read as a string and zero-padded to 5 digits.
- `street` is an anonymized ID, so demo addresses must be generated.
- Clip price outliers ($0 and >$50M) and impossible dates.
- Zillow file is wide (one column per month) and needs reshaping to long format.
