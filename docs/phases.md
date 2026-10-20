# Development phases

Stack: React + TypeScript (Vite) · FastAPI · PostgreSQL · OpenAI API.
Types flow one way: FastAPI models → `backend/openapi.json` → `frontend/src/api/schema.d.ts`.

The plan was reordered after the Phase 1 review: the first AI feature moved into the
CRM-core milestone, as the professor requested.

| Milestone | Scope | Status |
|---|---|---|
| 1 Foundation | Repo, CI, schema + migrations, JWT auth, roles, React shell | Done |
| 2 CRM core + first AI feature | Clients, listings, lead pipeline, data import, rule-based scoring and matching, AI Next Step | Done |
| 3 Evidence, scheduling and offers | API inventory, AI transparency, security matrix, AI vs rules evaluation, calendar, offers | Built; evaluation ratings in progress |
| 4 Market trends and polish | Zillow trend chart, calendar drag-and-drop, AI prompt improvements from the evaluation | Next |
| 5 Dashboard and analytics | Conversion charts, Zillow market trends | Planned |
| 6 Evaluation and finalization | AI scenario evaluation log, security review, demo | Planned |

## Milestone 2 checklist

- [x] Data pipeline: clean 800 Illinois listings and 94,656 Zillow market rows (`prepare_data`, `load_data`)
- [x] Demo data: 2 agents, 40 clients, leads in every stage, interactions, shortlists, past viewings (`seed_demo`)
- [x] Client management: create, search, filter, edit, delete; profile, timeline, shortlist, best matches
- [x] Property listings: search, filters, sort, paging, detail, add listing, update price, shortlist for a client
- [x] Lead pipeline: 7-stage drag-and-drop board, stage history, lost reason, lead detail
- [x] Rule-based lead score (0–100) with a per-factor explanation
- [x] Rule-based property match score (0–100)
- [x] AI Next Step: summary, intent, one recommended action, reasoning, editable draft message;
      accept (logs to timeline) or dismiss; every suggestion stored; rule-based fallback
- [x] Agents see only their own clients and leads; brokers see everything
- [x] 30 automated tests

## Milestone 3 (Phase 3)

See [phase3-requirements.md](phase3-requirements.md) for every requirement and its status. In short: 38 endpoints, all tested and listed in [api-inventory.md](api-inventory.md); 136 security checks passing ([security-matrix.md](security-matrix.md)); the AI hardened with first-name-only input, untrusted notes and a grounding check ([ai-design.md](ai-design.md)); a 15-scenario AI vs rules evaluation ready to run ([ai-evaluation.md](ai-evaluation.md)); and appointments and offers that move the pipeline on their own. 60 automated tests.
