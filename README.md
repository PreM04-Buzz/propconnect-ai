# PropConnect AI

AI-enhanced real estate CRM and lead management platform.
CPSC-8985 Graduate Seminar Project, Governors State University (Team 2).

**Stack:** React + TypeScript (Vite) · FastAPI · PostgreSQL · OpenAI API
**Status:** Milestone 2 done: client management, property listings, lead pipeline and the AI Next Step. See [docs/phases.md](docs/phases.md).

**Windows?** Follow [docs/WINDOWS_SETUP.md](docs/WINDOWS_SETUP.md).

## Repository layout

```
propconnect-ai/
├── backend/                 FastAPI app
│   ├── app/
│   │   ├── api/             routes + auth/role dependencies
│   │   ├── core/            settings, password hashing, JWT
│   │   ├── db/              SQLAlchemy base + session
│   │   ├── models/          ORM models (users, clients, leads, properties, ...)
│   │   ├── schemas/         Pydantic request/response models
│   │   ├── services/        lead scoring, property matching, AI Next Step
│   │   └── scripts/         data prep/load, demo seed, password reset, export OpenAPI
│   ├── migrations/          Alembic
│   ├── tests/
│   └── openapi.json         generated API contract (committed)
├── frontend/                React + TypeScript
│   └── src/
│       ├── api/             typed client + generated schema.d.ts
│       ├── auth/            auth context, protected routes
│       ├── components/
│       └── pages/
├── data/                    local datasets (git-ignored), see data/README.md
├── docs/
├── .github/                 CI workflow, PR template
└── docker-compose.yml       local PostgreSQL
```

## Getting started

Prerequisites: Python 3.12, Node 20, Docker.

```bash
# 1. Database
docker compose up -d db

# 2. Backend  (http://localhost:8000, docs at /docs)
cd backend
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp ../.env.example .env                               # then edit JWT_SECRET and ADMIN_PASSWORD
alembic upgrade head
python -m app.scripts.seed                            # creates the first admin account
uvicorn app.main:app --reload

# 3. Frontend  (http://localhost:5173)
cd frontend
npm install
npm run dev
```

Sign in with the `ADMIN_EMAIL` / `ADMIN_PASSWORD` from `backend/.env`, then add agent accounts on the Team page.

### Load listings and demo data

Put the datasets in `data/raw/` (see [data/README.md](data/README.md)), then from `backend/`:

```bash
python -m app.scripts.prepare_data   # clean 800 Illinois listings + Zillow market data
python -m app.scripts.load_data      # load into PostgreSQL
python -m app.scripts.seed_demo      # 2 demo agents, 40 clients, leads in every stage
```

Demo agent logins: `maria.lopez@propconnect-demo.com` and `james.carter@propconnect-demo.com`,
password `DEMO_PASSWORD` from `.env` (default `DemoAgent2026`).

### AI Next Step

Set `OPENAI_API_KEY` in `backend/.env` to use the model (default `gpt-4o-mini`, change with `OPENAI_MODEL`).
Without a key, a rule-based assistant gives the same kind of suggestion, so the app always works.
The model only receives facts from the database and must return a fixed JSON shape; invalid output
falls back to the rules. Every suggestion and the agent's decision are stored in `ai_suggestions`.

## Keeping frontend types in sync

The frontend never hand-writes API types. After changing any backend route or schema:

```bash
cd backend && python -m app.scripts.export_openapi   # updates backend/openapi.json
cd ../frontend && npm run gen:api                    # updates src/api/schema.d.ts
```

Commit both files. CI fails if either is out of date, and `tsc` flags every frontend call the change breaks.

## Common tasks

| Task | Command |
|---|---|
| Run backend tests | `cd backend && pytest` |
| New migration after model changes | `cd backend && alembic revision --autogenerate -m "describe change"` |
| Type-check frontend | `cd frontend && npm run typecheck` |
| Reset a password | `cd backend && python -m app.scripts.reset_password <email> <new password>` |
| Recreate demo data | `cd backend && python -m app.scripts.seed_demo --reset` |

## Workflow

- `main` is protected. Work on a branch, open a PR, and have your teammate review it.
- CI must pass before merging.
- Never commit `.env`, API keys or the raw datasets.
