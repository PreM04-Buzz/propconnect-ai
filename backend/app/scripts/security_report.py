"""Security matrix: calls every endpoint as different people and checks the answer.

Callers: nobody (no token), a forged token, an expired token, agent A (owns the
records), agent B (another agent), and the broker.

Run from backend/:
    python -m app.scripts.security_report          # writes docs/security-matrix.md
The same checks run in the test suite (tests/test_security_matrix.py), so CI
fails if any endpoint stops being protected.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import (
    AiSuggestion, Appointment, Client, Lead, LeadStageHistory, Offer, Property, PropertyInterest, User,
)
from app.models.enums import (
    AppointmentType, LeadStage, OfferStatus, PropertyStatus, SuggestionSource, UserRole,
)

PUBLIC = {("GET", "/api/health"), ("POST", "/api/auth/login")}


@dataclass
class Check:
    group: str
    method: str
    path: str
    caller: str
    expected: str
    actual: str

    @property
    def passed(self) -> bool:
        return self.expected == self.actual


def _token(user_id: int, role: str, secret: str | None = None, minutes: int = 60) -> str:
    if secret is None and minutes > 0:
        return create_access_token(str(user_id), role)
    s = get_settings()
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": str(user_id), "role": role, "iat": now, "exp": now + timedelta(minutes=minutes)},
                      secret or s.jwt_secret, algorithm=s.jwt_algorithm)


def _seed(db) -> dict:
    users = {}
    for key, role in (("a", UserRole.agent), ("b", UserRole.agent), ("broker", UserRole.admin)):
        u = User(email=f"{key}@matrix.test", full_name=f"User {key}", role=role, hashed_password=hash_password("x" * 12))
        db.add(u)
        db.flush()
        users[key] = u
    a = users["a"]
    p1 = Property(status=PropertyStatus.for_sale, price=300000, bedrooms=2, bathrooms=1, house_size_sqft=900,
                  street_address="1 Test St", city="Chicago", state="Illinois", zip_code="60601")
    p2 = Property(status=PropertyStatus.for_sale, price=320000, bedrooms=2, bathrooms=1, house_size_sqft=950,
                  street_address="2 Test St", city="Chicago", state="Illinois", zip_code="60601")
    db.add_all([p1, p2])
    db.flush()
    c = Client(agent_id=a.id, first_name="Owned", last_name="ByA", budget_max=350000, preferred_city="Chicago")
    db.add(c)
    db.flush()
    lead = Lead(client_id=c.id, agent_id=a.id, stage=LeadStage.qualified)
    db.add(lead)
    db.flush()
    db.add(LeadStageHistory(lead_id=lead.id, from_stage=None, to_stage=LeadStage.qualified, changed_by_id=a.id))
    pi = PropertyInterest(client_id=c.id, property_id=p1.id, interest_level="high")
    now = datetime.now(timezone.utc)
    ap = Appointment(agent_id=a.id, client_id=c.id, property_id=p1.id, appointment_type=AppointmentType.viewing,
                     starts_at=now + timedelta(days=2), ends_at=now + timedelta(days=2, hours=1))
    of = Offer(client_id=c.id, property_id=p1.id, lead_id=lead.id, amount=290000, status=OfferStatus.submitted)
    db.add_all([pi, ap, of])
    db.flush()
    sg = AiSuggestion(lead_id=lead.id, client_id=c.id, agent_id=a.id, source=SuggestionSource.rules,
                      intent_level="high", summary="s", recommended_action="r", action_type="call",
                      reasoning="r", draft_message="d")
    db.add(sg)
    db.commit()
    return {"users": users, "client": c.id, "lead": lead.id, "interest": pi.id, "prop": p2.id, "prop1": p1.id,
            "appt": ap.id, "offer": of.id, "sugg": sg.id}


def run() -> list[Check]:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    event.listen(engine, "connect", lambda c, _: c.execute("PRAGMA foreign_keys=ON"))
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(engine)
    db = Session()
    ids = _seed(db)
    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = lambda: db
    checks: list[Check] = []
    try:
        client = TestClient(app)
        u = ids["users"]
        hdr = lambda t: {"Authorization": f"Bearer {t}"}  # noqa: E731
        tok_a, tok_b = _token(u["a"].id, "agent"), _token(u["b"].id, "agent")
        tok_broker = _token(u["broker"].id, "admin")
        forged = _token(u["a"].id, "agent", secret="not-the-real-secret-not-the-real-secret")
        expired = _token(u["a"].id, "agent", minutes=-5)

        def fill(path: str) -> str:
            return (path.replace("{client_id}", str(ids["client"])).replace("{lead_id}", str(ids["lead"]))
                    .replace("{interest_id}", str(ids["interest"])).replace("{property_id}", str(ids["prop"]))
                    .replace("{appointment_id}", str(ids["appt"])).replace("{offer_id}", str(ids["offer"]))
                    .replace("{suggestion_id}", str(ids["sugg"])))

        def call(method, path, token=None, body=None):
            return client.request(method, path, headers=hdr(token) if token else {}, json=body).status_code

        # 1) Every protected endpoint refuses missing, forged and expired tokens.
        # Taken from the OpenAPI schema, so a new endpoint is checked automatically.
        routes = sorted((m.upper(), path) for path, ops in app.openapi()["paths"].items() for m in ops)
        for method, path in routes:
            if (method, path) in PUBLIC:
                continue
            for caller, token in (("no token", None), ("forged token", forged), ("expired token", expired)):
                checks.append(Check("Sign-in required", method, path, caller, "401",
                                    str(call(method, fill(path), token))))

        # 2) Agent B can't touch agent A's records by calling the API directly (404, not 403: no id probing).
        c, l, ap, of = ids["client"], ids["lead"], ids["appt"], ids["offer"]
        soon = datetime.now(timezone.utc) + timedelta(days=5)
        cross = [
            ("GET", f"/api/clients/{c}", None), ("PATCH", f"/api/clients/{c}", {"phone": "1"}),
            ("DELETE", f"/api/clients/{c}", None),
            ("POST", f"/api/clients/{c}/interactions", {"interaction_type": "call", "summary": "x"}),
            ("POST", f"/api/clients/{c}/interests", {"property_id": ids["prop"]}),
            ("DELETE", f"/api/clients/{c}/interests/{ids['interest']}", None),
            ("GET", f"/api/clients/{c}/matches", None),
            ("POST", "/api/leads", {"client_id": c}), ("GET", f"/api/leads/{l}", None),
            ("PATCH", f"/api/leads/{l}", {"source": "x"}), ("POST", f"/api/leads/{l}/move", {"to_stage": "won"}),
            ("POST", f"/api/leads/{l}/ai/next-step", None), ("GET", f"/api/leads/{l}/ai/suggestions", None),
            ("POST", f"/api/ai/suggestions/{ids['sugg']}/decision", {"status": "accepted"}),
            ("POST", "/api/appointments", {"client_id": c, "appointment_type": "meeting",
                                           "starts_at": soon.isoformat(), "ends_at": (soon + timedelta(hours=1)).isoformat()}),
            ("PATCH", f"/api/appointments/{ap}", {"notes": "x"}),
            ("POST", f"/api/appointments/{ap}/status", {"status": "cancelled"}),
            ("POST", "/api/offers", {"client_id": c, "property_id": ids["prop"], "amount": 1}),
            ("POST", f"/api/offers/{of}/status", {"status": "withdrawn"}),
        ]
        for method, path, body in cross:
            checks.append(Check("Other agent's records", method, path, "agent B", "404",
                                str(call(method, path, tok_b, body))))

        # 3) Lists only ever show your own records.
        for path, key in (("/api/clients", "id"), ("/api/leads", "client_id"), ("/api/appointments", "client_id"),
                          ("/api/offers", "client_id")):
            rows = client.get(path, headers=hdr(tok_b)).json()
            leaked = any(r.get(key) == c for r in rows)
            checks.append(Check("Lists show own records only", "GET", path, "agent B",
                                "no other agent's rows", "leaked" if leaked else "no other agent's rows"))

        # 4) Broker-only actions.
        for method, path, body in (("GET", "/api/users", None),
                                   ("POST", "/api/users", {"email": "x@y.com", "full_name": "X", "password": "x" * 10}),
                                   ("DELETE", f"/api/properties/{ids['prop']}", None)):
            checks.append(Check("Broker only", method, path, "agent A", "403", str(call(method, path, tok_a, body))))

        # 5) The rightful owner and the broker do get in.
        for caller, token in (("agent A (owner)", tok_a), ("broker", tok_broker)):
            checks.append(Check("Owner and broker allowed", "GET", f"/api/clients/{c}", caller, "200",
                                str(call("GET", f"/api/clients/{c}", token))))
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous
        db.close()
    return checks


def to_markdown(checks: list[Check]) -> str:
    passed = sum(ch.passed for ch in checks)
    groups: dict[str, list[Check]] = {}
    for ch in checks:
        groups.setdefault(ch.group, []).append(ch)
    lines = ["# Security matrix", "",
             f"Generated by `python -m app.scripts.security_report` on {datetime.now().date()}. "
             f"The same checks run in CI (`tests/test_security_matrix.py`).", "",
             f"**{passed} of {len(checks)} checks passed.**", "",
             "| Check | Calls | Passed |", "| --- | --- | --- |"]
    for g, rows in groups.items():
        lines.append(f"| {g} | {len(rows)} | {sum(r.passed for r in rows)} |")
    for g, rows in groups.items():
        lines += ["", f"## {g}", "", "| Method | Endpoint | Caller | Expected | Actual | |", "| --- | --- | --- | --- | --- | --- |"]
        for r in rows:
            lines.append(f"| {r.method} | `{r.path}` | {r.caller} | {r.expected} | {r.actual} | {'✅' if r.passed else '❌'} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    checks = run()
    out = Path(__file__).resolve().parents[3] / "docs" / "security-matrix.md"
    out.write_text(to_markdown(checks), encoding="utf-8")
    failed = [c for c in checks if not c.passed]
    print(f"{len(checks) - len(failed)} of {len(checks)} checks passed. Wrote {out}")
    for f in failed:
        print(f"  FAILED: {f.caller} {f.method} {f.path}: expected {f.expected}, got {f.actual}")


if __name__ == "__main__":
    main()
