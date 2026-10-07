# Development phases

Stack: React + TypeScript (Vite) · FastAPI · PostgreSQL · OpenAI API.
Types flow one way: FastAPI models → `backend/openapi.json` → `frontend/src/api/schema.d.ts`.

The plan was reordered after the Phase 1 review: the first AI feature moved into the
CRM-core milestone, as the professor requested.

| Milestone | Scope | Status |
|---|---|---|
| 1 Foundation | Repo, CI, schema + migrations, JWT auth, roles, React shell | Done |
| 2 CRM core + first AI feature | Clients, listings, lead pipeline, data import, rule-based scoring and matching, AI Next Step | Done |
| 3 Scheduling and offers | Calendar, viewings, conflict detection, offers | Next |
| 4 AI depth | Interaction summaries, AI explanations of matches, prompt evaluation | Planned |
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
