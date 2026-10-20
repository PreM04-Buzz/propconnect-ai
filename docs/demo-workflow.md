# End-to-end demo workflow

This is the script for the recorded demo: one deal from a new client to a closed sale, plus the security checks. It takes about 6 minutes. Record it in one take.

## Before you start

From `backend/`, with the virtual environment active:

```
python -m app.scripts.seed_demo --reset     # fresh demo data
uvicorn app.main:app --reload
```

and in a second window, from `frontend/`: `npm run dev`. Then open http://localhost:5173.

Logins: broker `admin@propconnect-demo.com` (your `ADMIN_PASSWORD`), agents `maria.lopez@propconnect-demo.com` and `james.carter@propconnect-demo.com` (password `DemoAgent2026`).

## The walkthrough

| # | Do this | You should see |
| --- | --- | --- |
| 1 | Sign in as the broker, open **Team**, add an agent | The new agent appears in the list |
| 2 | Sign out, sign in as Maria, open **Clients → Add client**, create a buyer | The profile opens; a lead starts in New |
| 3 | On the profile, click **Shortlist** on two of the best matches | Both appear under "Interested in"; the score goes up |
| 4 | Open the lead, click **Suggest next step**, edit the draft, click **Accept and log** | The suggestion is logged on the client's timeline |
| 5 | Click **Schedule**, book a viewing tomorrow at 10:00 | It appears on the calendar; the lead score rises by 10 |
| 6 | Book another appointment tomorrow at 10:30 | Blocked: "That time overlaps your viewing with…" |
| 7 | On the calendar, click **Done** on the viewing and type feedback | The viewing shows as completed, with the feedback |
| 8 | On the lead page, choose a shortlisted home, enter an amount, **Submit offer** | The lead moves to Negotiation on its own |
| 9 | On **Offers**, click **Seller countered**, enter an amount, then **Accepted** | The lead moves to Won; the home shows as sold |
| 10 | Open http://localhost:8000/docs, sign in as James, call `GET /api/clients/{id}` with the new client's id | 404 Not Found: James can't see Maria's client |
| 11 | Sign in to the app as the broker, open **Clients** | The broker sees every agent's clients |

## Evidence to show alongside

- `pytest` passing (60+ tests)
- [security-matrix.md](security-matrix.md): every endpoint, every caller
- [api-inventory.md](api-inventory.md): every endpoint, who can call it, and its tests
- A green GitHub Actions run
