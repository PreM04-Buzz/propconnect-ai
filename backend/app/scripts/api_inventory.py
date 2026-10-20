"""API inventory, generated from the running code rather than written by hand.

For every endpoint it lists what it does, who may call it (worked out from the
security matrix, so it's measured, not claimed), and how many automated tests
call it directly.

Run from backend/:
    python -m app.scripts.api_inventory      # writes docs/api-inventory.md
"""
import re
from collections import Counter
from datetime import date
from pathlib import Path

from app.main import app
from app.scripts import security_report

ROOT = Path(__file__).resolve().parents[3]
CALL = re.compile(r"client\.(get|post|patch|delete|put)\(\s*f?[\"'](/api/[^\"'?]+)")


def _shape(path: str) -> str:
    """'/api/clients/{cid}/interests' and '/api/clients/{client_id}/interests' -> same shape."""
    return re.sub(r"\{[^}]+\}|\d+", "{}", path)


def direct_test_counts() -> Counter:
    counts: Counter = Counter()
    for f in (ROOT / "backend" / "tests").glob("test_*.py"):
        for method, path in CALL.findall(f.read_text(encoding="utf-8")):
            counts[(method.upper(), _shape(path))] += 1
    return counts


def build() -> tuple[list[dict], dict]:
    checks = security_report.run()
    by_endpoint: dict[tuple[str, str], list] = {}
    for ch in checks:
        by_endpoint.setdefault((ch.method, _shape(ch.path)), []).append(ch)
    tests = direct_test_counts()
    rows = []
    for path, ops in app.openapi()["paths"].items():
        for method, op in ops.items():
            m, shape = method.upper(), _shape(path)
            groups = {c.group for c in by_endpoint.get((m, shape), [])}
            if "security" not in op:
                access = "Public"
            elif "Broker only" in groups:
                access = "Broker only"
            elif "Other agent's records" in groups:
                access = "Owner or broker"
            elif "Lists show own records only" in groups:
                access = "Signed in, own records only"
            else:
                access = "Any signed-in user"
            purpose = (op.get("description") or op.get("summary") or "").strip().split("\n")[0]
            rows.append({"method": m, "path": path, "tag": (op.get("tags") or ["other"])[0], "purpose": purpose,
                         "access": access, "tests": tests.get((m, shape), 0),
                         "checks": sum(c.passed for c in by_endpoint.get((m, shape), [])),
                         "checks_total": len(by_endpoint.get((m, shape), []))})
    rows.sort(key=lambda r: (r["tag"], r["path"], ["GET", "POST", "PATCH", "PUT", "DELETE"].index(r["method"])))
    summary = {
        "total": len(rows),
        "protected": sum(r["access"] != "Public" for r in rows),
        "tested": sum(r["tests"] > 0 for r in rows),
        "checks": sum(r["checks"] for r in rows),
        "checks_total": sum(r["checks_total"] for r in rows),
    }
    return rows, summary


def to_markdown(rows: list[dict], s: dict) -> str:
    lines = [
        "# API inventory", "",
        f"Generated from the code by `python -m app.scripts.api_inventory` on {date.today()}.", "",
        f"**{s['total']} endpoints are implemented.** {s['protected']} need a valid sign-in token; the other "
        f"{s['total'] - s['protected']} (health check and login) are public on purpose. "
        f"{s['tested']} have at least one direct automated test, and the security matrix made "
        f"{s['checks_total']} calls against them ({s['checks']} passed).", "",
        "**Who can call it:** *Public* needs no sign-in · *Any signed-in user* needs a valid token · "
        "*Own records only* lists only the caller's data · *Owner or broker* returns 404 to any other agent · "
        "*Broker only* returns 403 to agents.", "",
    ]
    tag = None
    for r in rows:
        if r["tag"] != tag:
            tag = r["tag"]
            lines += ["", f"## {'AI' if tag == 'ai' else tag.capitalize()}", "",
                      "| Method | Endpoint | What it does | Who can call it | Direct tests | Security checks |",
                      "| --- | --- | --- | --- | --- | --- |"]
        sec = f"{r['checks']}/{r['checks_total']}" if r["checks_total"] else "–"
        lines.append(f"| {r['method']} | `{r['path']}` | {r['purpose']} | {r['access']} | {r['tests']} | {sec} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    rows, s = build()
    out = ROOT / "docs" / "api-inventory.md"
    out.write_text(to_markdown(rows, s), encoding="utf-8")
    print(f"{s['total']} endpoints, {s['protected']} protected, {s['tested']} with direct tests. Wrote {out}")
    for r in rows:
        if r["tests"] == 0:
            print(f"  no direct test yet: {r['method']} {r['path']}")


if __name__ == "__main__":
    main()
