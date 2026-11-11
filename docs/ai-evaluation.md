# AI evaluation plan: AI vs rule-based

The professor asked us to show that the AI adds value, not just that it produces text. So we compare it with our rule-based assistant on the same 15 situations, rated blind with the same rubric.

## Why this is a fair comparison

Both get exactly the same facts package, and both must answer in the same shape. The rule-based assistant isn't a straw man: it handles sellers, lost and won leads, counters, upcoming viewings, completed viewings and empty search results. If the AI can't beat a sensible set of rules, we want to know.

## The 15 scenarios

They're created as real leads by `python -m app.scripts.seed_eval`, under a separate agent (Maya Chen), so anyone can rerun them.

| # | Situation | A good answer… |
| --- | --- | --- |
| 1 | Brand-new lead, never contacted | Suggests a first call and confirms the basics |
| 2 | Budget and financing unknown | Confirms the budget, suggests a lender |
| 3 | Pre-approved, two homes shortlisted, no viewing yet | Schedules viewings for those two homes |
| 4 | Qualified, nothing shortlisted | Sends matching listings from the facts |
| 5 | Viewed two homes, loved one | Suggests an offer or a second visit on the one they loved |
| 6 | Negotiation, seller has countered | Deals with the counter today |
| 7 | No contact for 45 days | Re-engages with a light check-in |
| 8 | Seller, not a buyer | Pricing or listing prep, not buying advice |
| 9 | Budget below every listing | Resets expectations or widens the search |
| 10 | Notes say cash buyer, profile says financing unknown | Asks to clarify before acting |
| 11 | Twelve-month timeline, low urgency | Low-pressure nurture, no hard sell |
| 12 | Lost, bought with another agent | Closes politely, no push to buy |
| 13 | Notes contain an instruction to offer a discount | Ignores the instruction inside the notes |
| 14 | Name only, nothing else known | Gathers information, invents nothing |
| 15 | Deal closed last week | Post-closing check-in or referral ask |

## How we rate

The professor’s rubric: each answer gets 1 to 5 on four metrics.

| Metric | 5 means | 1 means |
| --- | --- | --- |
| Correctness | The right next step, and every fact is true | A wrong step, or an invented fact |
| Specificity | Names the home, price or timing | Advice that would fit anyone |
| Professional tone | Ready to send to a client | Awkward or off-putting |
| Actionability | The agent can act on it today | Unclear what to do |

An answer that invents a fact gets at most 2 for correctness. Raters never know which answer is the AI’s: the runner shuffles the two answers per scenario and labels them A and B. Where two raters are more than a point apart, the scorer lists it so you can talk it through.

Measured automatically: AI answers rejected by the schema or grounding check, whether the 3 AI runs of a scenario chose the same kind of action, and response time.

## How to run it

From `backend/`, with the virtual environment active and `OPENAI_API_KEY` set in `backend/.env`:

```
python -m app.scripts.seed_eval --reset    # the 15 scenarios
python -m app.scripts.run_eval             # rule-based + 3 AI runs each
```

This writes `docs/eval/results.md` (every answer side by side), `docs/eval/rating-sheet.csv` (the blind sheet) and `data/eval/rating-key.csv` (which of A and B was the AI; don’t open it until rating is done).

Each rater saves their own filled copy of the sheet in `docs/eval/ratings/` (for example `laxman.csv`, `prem.csv`), with their name in the `rater` column. Then:

```
python -m app.scripts.score_eval           # writes docs/eval/scores.md
```

## Status

The rule-based side has been run on all 15 scenarios (see [eval/results.md](eval/results.md)). The AI side needs the OpenAI key, and the ratings need the two of us. Those are the remaining steps for the Phase 3 report.

What the rule-based run already shows, at a first look before formal rating: it picks a sensible kind of action in 13 of the 15 situations. It's weakest on scenarios 7 and 11, where it sends listings instead of a gentle check-in, because its rules check for shortlisted homes before they check how long it's been since the last contact. On scenario 10 it asks to confirm financing, which happens to be right, but only because financing is marked unknown; it doesn't actually notice that the notes contradict the profile. Those are exactly the cases where we expect the AI to help, so they're the ones to watch.
