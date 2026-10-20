# Traceability: requirement → code → test → screen

Each Phase 3 requirement and where you can see it working.

| Req | What | Endpoints | Tests | Screen or document |
| --- | --- | --- | --- | --- |
| R1.1 | API inventory generated from the code | all | `api_inventory` script | docs/api-inventory.md |
| R1.2 | Every endpoint has a direct test | all | `test_endpoint_gaps.py` and others | docs/api-inventory.md ("Direct tests" column) |
| R2.1 | Real sample prompt and response | – | `ai_sample` script | docs/ai-sample.md |
| R2.2 | First name only to the model | `POST /api/leads/{id}/ai/next-step` | `test_ai_v2.py::test_model_gets_first_name_only_and_notes_as_untrusted` | docs/ai-design.md |
| R2.3 | Grounding check | same | `test_grounding.py`, `test_ai_v2.py::test_an_invented_price_sends_us_to_the_rules` | Lead page, "Checked against client data" badge |
| R2.4 | Notes passed as untrusted | same | `test_ai_v2.py` (first test); evaluation scenario 13 | docs/ai-design.md |
| R2.5 | Prompt version stored | same | `test_ai_v2.py` (first test) | `ai_suggestions.prompt_version` |
| R3.1 | Security matrix on every endpoint | all | `test_security_matrix.py` (136 checks) | docs/security-matrix.md |
| R3.2 | No endpoint can be left unprotected | all | same, endpoint list read from OpenAPI | docs/security-matrix.md |
| R3.3 | Sign-in lockout | `POST /api/auth/login` | `test_account_security.py` (2 tests) | Login page shows "Too many failed sign-in attempts" |
| R3.4 | Refuse dev secrets in production | startup | `test_account_security.py::test_production_refuses_development_secrets` | – |
| R4 | AI vs rule-based evaluation | – | `seed_eval`, `run_eval`, `score_eval` scripts | docs/ai-evaluation.md, docs/eval/ |
| R5.1 | ER diagram | – | – | docs/erd.md |
| R5.2 | End-to-end demo | – | – | docs/demo-workflow.md |
| F1 | Schedule an appointment | `POST /api/appointments` | `test_appointments.py::test_schedule_and_list_a_viewing` | Calendar → Schedule |
| F2 | Week view | `GET /api/appointments` | same | Calendar |
| F3 | Double-booking check | `POST`, `PATCH /api/appointments` | `test_double_booking_is_blocked`, `test_rescheduling_checks_for_clashes` | Calendar error message |
| F4 | Complete, cancel, no-show | `POST /api/appointments/{id}/status` | `test_viewings_count_in_the_score_and_completing_needs_feedback` | Calendar card buttons |
| F5 | Offers and their statuses | `POST /api/offers`, `POST /api/offers/{id}/status` | `test_offers.py` (7 tests) | Offers page, lead page |
| F6 | Offers move the pipeline | same | `test_submitting_an_offer_moves_the_lead_to_negotiation`, `test_accepting_wins_the_lead_and_sells_the_property` | Pipeline board |
| F7 | AI sees viewings and offers | `POST /api/leads/{id}/ai/next-step` | `test_ai_v2.py::test_viewings_and_offers_reach_the_facts` | Lead page |
| F8 | Change your own password | `POST /api/users/me/password` | `test_account_security.py::test_change_own_password` | Account page |
