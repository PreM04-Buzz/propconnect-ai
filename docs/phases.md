# Development phases

Stack: React + TypeScript (Vite) · FastAPI · PostgreSQL · OpenAI API (Phase 5).
Types flow one way: FastAPI models → `backend/openapi.json` → `frontend/src/api/schema.d.ts`.

| Phase | Name | Outcome |
|---|---|---|
| 1 | Foundation | Repo, CI, full DB schema + migrations, JWT auth, roles, React shell |
| 2 | CRM core + data | Clients, leads, pipeline moves with history, properties, interactions; dataset cleaning + import |
| 3 | Scheduling & offers | Calendar views, viewings/meetings, conflict detection, offers |
| 4 | Matching & scoring | Rule-based 0-100 property match and lead score, with explanations and unit tests |
| 5 | AI Lead Assistant | Backend-only LLM calls, bounded prompts, summaries, next actions, drafts, agent review |
| 6 | Dashboard & analytics | KPIs, pipeline and conversion charts, Zillow market trends |
| 7 | Evaluation & finalization | AI scenario evaluation log, security review, bug fixes, demo scenarios |

## Phase 1 - Foundation (this scaffold)

- [x] Monorepo layout, `.gitignore`, `.env.example`, Docker Postgres
- [x] SQLAlchemy models for every entity in the design doc
- [x] Initial Alembic migration
- [x] Password hashing (bcrypt) and JWT access tokens
- [x] Role-based access: `agent`, `admin` (Administrator/Broker)
- [x] API: `/api/health`, `/api/auth/login`, `/api/auth/me`, `/api/users` (admin only)
- [x] Seed script for the first admin
- [x] OpenAPI export → generated TypeScript types → typed API client
- [x] React shell: login, protected routes, role-gated Team page, sidebar
- [x] CI: tests, migrations on real Postgres, schema drift checks, frontend build
- [ ] Create the GitHub repo, protect `main`, add teammate as collaborator
- [ ] Create a GitHub Projects board with one column per phase
