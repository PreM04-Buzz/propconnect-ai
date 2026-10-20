"""Grounding check: does an AI answer only mention facts we actually gave it?

The schema check makes sure the answer has the right shape. This check looks at
what it says: every dollar amount, street address and ISO date in the answer has
to appear in the facts package. If not, the answer is rejected.

It's deliberately simple and conservative. It can't catch every made-up claim,
but it reliably catches the ones that would embarrass an agent: a wrong price,
an address that doesn't exist, a date nobody agreed to.
"""
import json
import re

MONEY = re.compile(r"\$\s?(\d[\d,]*(?:\.\d+)?)\s*([kKmM])?\b")
ADDRESS = re.compile(r"\b(\d{1,5})\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\s+(St|Ave|Dr|Ln|Ct|Rd|Way|Blvd|Pl)\b")
ISO_DATE = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")


def _amounts(text: str) -> set[int]:
    out = set()
    for num, unit in MONEY.findall(text):
        value = float(num.replace(",", ""))
        if unit and unit.lower() == "k":
            value *= 1_000
        elif unit and unit.lower() == "m":
            value *= 1_000_000
        out.add(round(value))
    return out


def _close(a: int, known: set[int]) -> bool:
    # "$400K" for $400,000 is fine; allow half a percent of rounding either way.
    return any(abs(a - k) <= max(1, k * 0.005) for k in known)


def check(answer: dict, facts: dict) -> tuple[bool, list[str]]:
    facts_text = json.dumps(facts, default=str)
    text = " ".join(str(answer.get(k, "")) for k in
                    ("summary", "recommended_action", "reasoning", "draft_message"))
    issues = []

    known_amounts = _amounts(facts_text)
    for a in sorted(_amounts(text)):
        if not _close(a, known_amounts):
            issues.append(f"mentions ${a:,} which isn't in the client's data")

    for number, street, suffix in ADDRESS.findall(text):
        addr = f"{number} {street} {suffix}"
        if addr not in facts_text:
            issues.append(f"mentions {addr}, which isn't one of the client's properties")

    for d in sorted(set(ISO_DATE.findall(text))):
        if d not in facts_text:
            issues.append(f"mentions the date {d}, which isn't in the data")

    return (not issues, issues)
