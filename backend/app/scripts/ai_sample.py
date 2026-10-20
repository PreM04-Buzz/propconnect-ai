"""Print one real AI exchange for the report: the exact prompt, the facts sent,
and the answers from the rule-based assistant and (if a key is set) the model.

Run from backend/:
    python -m app.scripts.ai_sample                  # uses evaluation scenario 3 (Aisha)
    python -m app.scripts.ai_sample --scenario 6
Writes docs/ai-sample.md
"""
import argparse
import json
from datetime import date
from pathlib import Path

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import Client, Lead
from app.scripts.seed_eval import SCENARIOS
from app.services import grounding
from app.services.ai_assistant import PROMPT_VERSION, SYSTEM_PROMPT, ask_model, build_context, rule_based

ROOT = Path(__file__).resolve().parents[3]


def block(answer: dict) -> list[str]:
    return ["```json", json.dumps(answer, indent=2), "```"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", type=int, default=3)
    n = ap.parse_args().scenario
    title = next(t for k, t, _ in SCENARIOS if k == n)
    s = get_settings()
    with SessionLocal() as db:
        c = db.scalar(select(Client).where(Client.email == f"eval-{n:02d}@example.com"))
        if c is None:
            raise SystemExit("Create the scenarios first: python -m app.scripts.seed_eval")
        ctx = build_context(db, db.scalar(select(Lead).where(Lead.client_id == c.id)))
    rules = rule_based(ctx).model_dump()
    lines = [f"# Sample AI exchange: scenario {n}, {title}", "",
             f"Captured with `python -m app.scripts.ai_sample --scenario {n}` on {date.today()}, prompt {PROMPT_VERSION}.", "",
             "## 1. System message (the prompt)", "", "```text", SYSTEM_PROMPT.strip(), "```", "",
             "## 2. User message (the facts package, exactly as sent)", "", "```json",
             json.dumps(ctx, indent=2, default=str), "```", "",
             "## 3. Rule-based answer", ""] + block(rules)
    ok, issues = grounding.check(rules, ctx)
    lines += ["", f"Grounding check: {'passed' if ok else 'failed: ' + '; '.join(issues)}."]
    lines += ["", "## 4. Model answer", ""]
    if s.openai_api_key:
        out, problems, secs = ask_model(ctx)
        if out:
            lines += [f"Model `{s.openai_model}`, {secs:.1f} seconds. Passed the schema and grounding checks.", ""]
            lines += block(out.model_dump())
        else:
            lines += [f"The model's answer was rejected ({'; '.join(problems)}), so the agent would see the rule-based answer."]
    else:
        lines += ["Not captured yet: add `OPENAI_API_KEY` to `backend/.env` and run this script again."]
    out_path = ROOT / "docs" / "ai-sample.md"
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
