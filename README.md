# PropConnect AI

AI-enhanced real estate CRM and lead management platform.
CPSC-8985 Graduate Seminar Project, Governors State University (Team 2).

**Stack:** React + TypeScript (Vite) · FastAPI · PostgreSQL · OpenAI API
**Status:** Phase 1 (Foundation). See [docs/phases.md](docs/phases.md).

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
│   │   └── scripts/         seed admin, export OpenAPI
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

## Workflow

- `main` is protected. Work on a branch, open a PR, and have your teammate review it.
- CI must pass before merging.
- Never commit `.env`, API keys or the raw datasets.
