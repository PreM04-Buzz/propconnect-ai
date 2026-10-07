"""AI Next Step: suggests the single most useful next action for a lead.

Design rules (from the design document):
- The AI only suggests. The agent accepts, edits or dismisses.
- The model sees only facts from our database, and must return a fixed JSON shape.
- Scores stay rule-based; the AI explains and recommends, it never scores.
- If the API key is missing, the call fails, or the output is invalid, a
  deterministic rule-based suggestion is used instead, so the CRM never breaks.
"""
import json
import logging
from datetime import datetime, timezone

import httpx
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import AiSuggestion, Appointment, Client, Interaction, Lead, PropertyInterest, User
from app.models.enums import AppointmentType, SuggestionSource
from app.schemas.ai import ACTION_TYPES, AiOutput
from app.services.lead_scoring import compute_score
from app.services.matching import top_matches

log = logging.getLogger(__name__)

SYSTEM_PROMPT = f"""You are an assistant inside a real estate CRM. You help a licensed agent decide
the single most useful next step with one client. The agent makes the final decision.

Rules:
- Use ONLY the facts in the JSON you are given. Never invent properties, prices, dates or client details.
- If important information is missing (budget, financing, timeline), recommend gathering it.
- Be specific: name the property address or price when recommending a viewing or listings.
- Keep a warm, professional tone in the draft message. Sign it with the agent's first name.

Respond with a single JSON object and nothing else, with exactly these keys:
  "intent_level": "high" | "medium" | "low"  (how ready the client is to buy or sell)
  "summary": what the client wants and where they stand, at most 60 words
  "recommended_action": one concrete next step, at most 40 words
  "action_type": one of {", ".join(ACTION_TYPES)}
  "reasoning": why this step, citing facts from the data, at most 60 words
  "draft_message": a message the agent could send to the client, at most 120 words
"""


def _money(v) -> str | None:
    return f"${float(v):,.0f}" if v is not None else None


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def build_context(db: Session, lead: Lead) -> dict:
    """Collect the facts the model is allowed to use."""
    c: Client = lead.client
    agent = db.get(User, lead.agent_id)
    now = datetime.now(timezone.utc)
    score = compute_score(db, c, now)

    interactions = list(db.scalars(
        select(Interaction).where(Interaction.client_id == c.id).order_by(Interaction.occurred_at.desc()).limit(8)
    ))
    interests = list(db.scalars(select(PropertyInterest).where(PropertyInterest.client_id == c.id)))
    viewings = db.scalar(select(func.count(Appointment.id)).where(
        Appointment.client_id == c.id, Appointment.appointment_type == AppointmentType.viewing)) or 0

    stage_entered = lead.history[-1].changed_at if lead.history else lead.created_at
    ctx = {
        "agent_first_name": (agent.full_name.split()[0] if agent else "Your agent"),
        "today": now.date().isoformat(),
        "client": {
            "name": f"{c.first_name} {c.last_name}",
            "type": c.client_type.value,
            "budget_min": _money(c.budget_min),
            "budget_max": _money(c.budget_max),
            "budget_confirmed": c.budget_confirmed,
            "preferred_city": c.preferred_city,
            "preferred_state": c.preferred_state,
            "min_bedrooms": c.min_bedrooms,
            "min_bathrooms": float(c.min_bathrooms) if c.min_bathrooms is not None else None,
            "financing_status": c.financing_status.value,
            "purchase_timeline_months": c.purchase_timeline_months,
            "notes": c.notes,
        },
        "lead": {
            "stage": lead.stage.value,
            "days_in_stage": max(0, (now - _aware(stage_entered)).days),
            "rule_based_score": score.score,
            "priority": score.priority,
            "score_reasons": [i.reason for i in score.items],
        },
        "recent_interactions": [
            {"date": _aware(i.occurred_at).date().isoformat(), "type": i.interaction_type.value, "summary": i.summary}
            for i in interactions
        ],
        "viewings_so_far": viewings,
        "properties_of_interest": [
            {"address": f"{pi.property.street_address}, {pi.property.city}", "price": _money(pi.property.price),
             "bedrooms": pi.property.bedrooms, "bathrooms": float(pi.property.bathrooms or 0),
             "interest_level": pi.interest_level}
            for pi in interests
        ],
    }
    if not interests and c.client_type.value != "seller":
        ctx["suggested_matching_listings"] = [
            {"address": f"{m.property.street_address}, {m.property.city}", "price": _money(m.property.price),
             "bedrooms": m.property.bedrooms, "match_score": m.score}
            for m in top_matches(db, c, limit=3)
        ]
    return ctx


def rule_based(ctx: dict) -> AiOutput:
    """Deterministic fallback. Same output shape as the model."""
    c, lead = ctx["client"], ctx["lead"]
    first = c["name"].split()[0]
    agent = ctx["agent_first_name"]
    intent = lead["priority"]
    interests = ctx["properties_of_interest"]
    listings = ctx.get("suggested_matching_listings") or []
    last = ctx["recent_interactions"][0]["date"] if ctx["recent_interactions"] else None
    wants = f"{c['min_bedrooms']}+ bedroom home" if c["min_bedrooms"] else "home"
    where = f" in {c['preferred_city']}" if c["preferred_city"] else ""
    budget = f" up to {c['budget_max']}" if c["budget_max"] else ""
    summary = (f"{c['name']} is a {c['type']} looking for a {wants}{where}{budget}. "
               f"The lead is in the {lead['stage']} stage with a rule-based score of {lead['rule_based_score']}/100.")

    if lead["stage"] == "new":
        action, kind = f"Call {first} to introduce yourself and confirm budget, timeline and financing.", "call"
        why = "New leads convert best with a prompt first call, and key details are still unconfirmed."
        msg = (f"Hi {first}, this is {agent}. Thanks for reaching out! I'd love to learn more about what you're "
               f"looking for{where}. Do you have 15 minutes this week for a quick call?")
    elif c["financing_status"] in ("unknown", "not_started") or not c["budget_confirmed"]:
        action, kind = f"Confirm {first}'s budget and financing, and suggest a lender for pre-approval.", "call"
        why = "Financing or budget is not confirmed, which blocks offers and lowers the lead score."
        msg = (f"Hi {first}, it's {agent}. To make sure we focus on the right homes, could we confirm your budget "
               f"and financing? I'm happy to connect you with a trusted lender for pre-approval.")
    elif lead["stage"] in ("proposal", "negotiation"):
        action, kind = f"Follow up with {first} on the current offer and next decision point.", "call"
        why = f"The lead is in {lead['stage']}; momentum matters most at this stage."
        msg = f"Hi {first}, it's {agent}. Just checking in on the offer. Do you have a few minutes today to talk through next steps?"
    elif interests and ctx["viewings_so_far"] == 0:
        top = sorted(interests, key=lambda p: {"high": 0, "medium": 1, "low": 2}[p["interest_level"]])[:2]
        names = " and ".join(p["address"] for p in top)
        action, kind = f"Schedule viewings for {names}.", "schedule_viewing"
        why = "The client has shown interest in specific properties but hasn't viewed any yet."
        msg = (f"Hi {first}, it's {agent}. Would you like to see {names} in person? "
               f"I have openings this week and can arrange both visits back to back.")
    elif listings:
        names = "; ".join(f"{l['address']} ({l['price']})" for l in listings)
        action, kind = f"Send {first} these matching listings: {names}.", "send_listings"
        why = "No properties have been shortlisted yet, and these listings match the stated preferences."
        msg = (f"Hi {first}, it's {agent}. I found a few homes that match what you described: {names}. "
               f"Let me know which ones you'd like to see!")
    else:
        action, kind = f"Check in with {first} to keep momentum and confirm next steps.", "email"
        why = f"Last contact was {last}." if last else "There is no recent contact on record."
        msg = f"Hi {first}, it's {agent}. Just checking in to see how your search is going and how I can help this week."
    return AiOutput(intent_level=intent, summary=summary[:800], recommended_action=action[:500],
                    action_type=kind, reasoning=why, draft_message=msg[:1500])


def _call_openai(ctx: dict) -> dict:
    s = get_settings()
    resp = httpx.post(
        f"{s.openai_base_url}/chat/completions",
        headers={"Authorization": f"Bearer {s.openai_api_key}"},
        json={
            "model": s.openai_model,
            "temperature": 0.3,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": "Client data:\n" + json.dumps(ctx, default=str)},
            ],
        },
        timeout=s.ai_timeout_seconds,
    )
    resp.raise_for_status()
    return json.loads(resp.json()["choices"][0]["message"]["content"])


def generate_suggestion(db: Session, lead: Lead, user: User) -> AiSuggestion:
    s = get_settings()
    ctx = build_context(db, lead)
    source, model, out = SuggestionSource.rules, None, None
    if s.openai_api_key:
        try:
            out = AiOutput.model_validate(_call_openai(ctx))
            source, model = SuggestionSource.openai, s.openai_model
        except (httpx.HTTPError, KeyError, json.JSONDecodeError, ValidationError) as exc:
            log.warning("AI call failed, using rule-based fallback: %s", exc)
    if out is None:
        out = rule_based(ctx)

    suggestion = AiSuggestion(
        lead_id=lead.id, client_id=lead.client_id, agent_id=user.id, source=source, model=model,
        **out.model_dump(),
    )
    db.add(suggestion)
    db.commit()
    db.refresh(suggestion)
    return suggestion
