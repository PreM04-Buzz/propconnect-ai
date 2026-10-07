"""Create realistic demo data: 2 agents, 40 clients, leads in every stage, interactions,
property interests and past viewings. Requires listings (run load_data first).

Run from backend/:
    python -m app.scripts.seed_demo            # once
    python -m app.scripts.seed_demo --reset    # delete demo agents' data and recreate it

Demo logins (password from DEMO_PASSWORD in .env, default DemoAgent2026):
    maria.lopez@propconnect-demo.com, james.carter@propconnect-demo.com
"""
import argparse
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import (
    AiSuggestion, Appointment, Client, Interaction, Lead, LeadStageHistory, Property, PropertyInterest, User,
)
from app.models.enums import (
    AppointmentStatus, AppointmentType, ClientType, FinancingStatus, InteractionType, LeadStage, PropertyStatus,
    UserRole,
)
from app.services.lead_scoring import refresh_client_leads
from app.services.matching import top_matches

AGENTS = [("Maria Lopez", "maria.lopez@propconnect-demo.com"), ("James Carter", "james.carter@propconnect-demo.com")]
FIRST = ["Olivia", "Liam", "Emma", "Noah", "Ava", "Ethan", "Sophia", "Mason", "Isabella", "Lucas", "Mia", "Daniel",
         "Priya", "Arjun", "Grace", "Samuel", "Chloe", "David", "Fatima", "Omar", "Hannah", "Kevin", "Leah", "Marcus",
         "Nina", "Ryan", "Sara", "Tyler", "Zoe", "Ben", "Jasmine", "Carlos", "Elena", "Jamal", "Mei", "Victor",
         "Rosa", "Andre", "Lily"]
LAST = ["Johnson", "Nguyen", "Garcia", "Smith", "Kim", "Brown", "Martinez", "Davis", "Wilson", "Anderson", "Thomas",
        "Moore", "Shah", "Reddy", "Clark", "Lewis", "Walker", "Young", "Khan", "Hill", "Scott", "Adams", "Baker",
        "Rivera", "Campbell", "Mitchell", "Roberts", "Turner", "Phillips", "Evans"]
SOURCES = ["Website", "Referral", "Open house", "Zillow inquiry", "Social media", "Walk-in"]
# Stage mix for 39 random leads (+1 showcase lead).
STAGES = ([LeadStage.new] * 7 + [LeadStage.contacted] * 8 + [LeadStage.qualified] * 7 + [LeadStage.proposal] * 5
          + [LeadStage.negotiation] * 4 + [LeadStage.won] * 4 + [LeadStage.lost] * 4)
ORDER = [LeadStage.new, LeadStage.contacted, LeadStage.qualified, LeadStage.proposal, LeadStage.negotiation,
         LeadStage.won]
NOTES = {
    LeadStage.contacted: ("call", "Intro call. Discussed must-haves and preferred neighborhoods."),
    LeadStage.qualified: ("meeting", "Buyer consultation. Confirmed budget, timeline and financing."),
    LeadStage.proposal: ("email", "Sent shortlist of homes and comparable sales."),
    LeadStage.negotiation: ("call", "Discussed counter-offer from the seller."),
    LeadStage.won: ("meeting", "Closing completed. Keys handed over."),
}


def _round(x: float, step: int = 5000) -> int:
    return int(round(x / step) * step)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true")
    args = ap.parse_args()
    rng = random.Random(7)
    now = datetime.now(timezone.utc)
    password = get_settings().demo_password

    with SessionLocal() as db:
        if not db.scalar(select(func.count(Property.id))):
            raise SystemExit("No listings found. Run: python -m app.scripts.load_data")

        agents = []
        for name, email in AGENTS:
            user = db.scalar(select(User).where(User.email == email))
            if user and not args.reset and db.scalar(select(func.count(Client.id)).where(Client.agent_id == user.id)):
                raise SystemExit("Demo data already exists. Use --reset to recreate it.")
            if user is None:
                user = User(email=email, full_name=name, role=UserRole.agent, hashed_password=hash_password(password))
                db.add(user)
                db.flush()
            agents.append(user)
        ids = [a.id for a in agents]
        client_ids = select(Client.id).where(Client.agent_id.in_(ids))
        for model in (AiSuggestion, Appointment, Interaction, PropertyInterest):
            db.execute(delete(model).where(model.client_id.in_(client_ids)))
        lead_ids = select(Lead.id).where(Lead.agent_id.in_(ids))
        db.execute(delete(AiSuggestion).where(AiSuggestion.lead_id.in_(lead_ids)))
        db.execute(delete(LeadStageHistory).where(LeadStageHistory.lead_id.in_(lead_ids)))
        db.execute(delete(Lead).where(Lead.agent_id.in_(ids)))
        db.execute(delete(Client).where(Client.agent_id.in_(ids)))
        db.flush()

        listings = list(db.scalars(select(Property).where(Property.status == PropertyStatus.for_sale)))
        city_counts: dict[str, int] = {}
        for p in listings:
            city_counts[p.city] = city_counts.get(p.city, 0) + 1
        popular = {c for c, n in city_counts.items() if n >= 5}
        anchors = [p for p in listings if p.city in popular and p.price and 120_000 <= float(p.price) <= 900_000]

        def add_history(lead: Lead, stage: LeadStage, start: datetime, agent: User) -> datetime:
            path = ORDER[: ORDER.index(stage) + 1] if stage != LeadStage.lost else ORDER[: rng.randint(2, 4)] + [LeadStage.lost]
            when, prev = start, None
            for s in path:
                db.add(LeadStageHistory(lead_id=lead.id, from_stage=prev, to_stage=s, changed_by_id=agent.id,
                                        changed_at=when))
                if s in NOTES:
                    kind, text = NOTES[s]
                    db.add(Interaction(client_id=lead.client_id, agent_id=agent.id,
                                       interaction_type=InteractionType(kind), summary=text, occurred_at=when))
                prev, when = s, when + timedelta(days=rng.randint(3, 9))
            return when

        def make_client(agent, first, last, anchor, stage, **over):
            price = float(anchor.price)
            ctype = over.pop("client_type", rng.choices([ClientType.buyer, ClientType.seller, ClientType.both],
                                                       [32, 5, 3])[0])
            c = Client(
                agent_id=agent.id, first_name=first, last_name=last, client_type=ctype,
                email=f"{first}.{last}@example.com".lower(), phone=f"(630) 555-{rng.randint(1000, 9999)}",
                budget_max=_round(price * rng.uniform(1.0, 1.2)), budget_min=_round(price * 0.7),
                budget_confirmed=stage not in (LeadStage.new,) and rng.random() < 0.8,
                preferred_city=anchor.city, preferred_state="Illinois",
                min_bedrooms=max(1, (anchor.bedrooms or 2) - rng.choice([0, 0, 1])),
                min_bathrooms=1, financing_status=rng.choice(list(FinancingStatus)) if stage == LeadStage.new
                else rng.choices([FinancingStatus.pre_approved, FinancingStatus.cash, FinancingStatus.pre_qualified,
                                  FinancingStatus.not_started], [5, 1, 2, 1])[0],
                purchase_timeline_months=rng.choice([1, 2, 3, 4, 6, 9, 12]), **over,
            )
            db.add(c)
            db.flush()
            lead = Lead(client_id=c.id, agent_id=agent.id, stage=LeadStage.new, source=rng.choice(SOURCES))
            db.add(lead)
            db.flush()
            start = now - timedelta(days=rng.randint(25, 75))
            if stage == LeadStage.new:
                start = now - timedelta(days=rng.randint(0, 4))
            end = add_history(lead, stage, start, agent)
            lead.stage = stage
            if stage == LeadStage.lost:
                lead.lost_reason = rng.choice(["Bought with another agent", "Paused search", "Budget changed"])
            return c, lead, min(end, now)

        # Showcase client for the demo: a high-intent buyer, two condos-sized homes shortlisted, no viewing yet.
        two_bed = [p for p in anchors if p.bedrooms == 2 and float(p.price) < 400_000]
        showcase_city = max({p.city for p in two_bed}, key=lambda c: sum(1 for p in two_bed if p.city == c))
        anchor = next(p for p in two_bed if p.city == showcase_city)
        c, lead, _ = make_client(agents[0], "Aisha", "Patel", anchor, LeadStage.qualified,
                                 client_type=ClientType.buyer)
        c.budget_max, c.budget_min, c.min_bedrooms = 400_000, 280_000, 2
        c.budget_confirmed, c.financing_status, c.purchase_timeline_months = True, FinancingStatus.pre_approved, 2
        c.notes = "Relocating for work in January. Wants a two-bedroom near transit."
        db.flush()
        for m in top_matches(db, c, limit=2):
            db.add(PropertyInterest(client_id=c.id, property_id=m.property.id, interest_level="high",
                                    notes="Asked about HOA fees and parking."))
        db.add(Interaction(client_id=c.id, agent_id=agents[0].id, interaction_type=InteractionType.email,
                           summary="Aisha replied: loved both listings, available most evenings next week.",
                           occurred_at=now - timedelta(days=2)))

        rng.shuffle(STAGES)
        used = {("Aisha", "Patel")}
        for i, stage in enumerate(STAGES):
            agent = agents[i % 2]
            while (name := (rng.choice(FIRST), rng.choice(LAST))) in used:
                pass
            used.add(name)
            c, lead, last = make_client(agent, *name, rng.choice(anchors), stage)
            if c.client_type != ClientType.seller and stage in (LeadStage.qualified, LeadStage.proposal,
                                                                LeadStage.negotiation, LeadStage.won):
                for m in top_matches(db, c, limit=rng.randint(1, 3)):
                    db.add(PropertyInterest(client_id=c.id, property_id=m.property.id,
                                            interest_level=rng.choice(["medium", "high"])))
                    if stage != LeadStage.qualified:
                        t = last - timedelta(days=rng.randint(1, 5))
                        db.add(Appointment(agent_id=agent.id, client_id=c.id, property_id=m.property.id,
                                           appointment_type=AppointmentType.viewing,
                                           status=AppointmentStatus.completed, starts_at=t,
                                           ends_at=t + timedelta(minutes=45),
                                           outcome=rng.choice(["Liked the layout", "Kitchen needs work",
                                                               "Wants a second visit"])))
            if stage == LeadStage.contacted and rng.random() < 0.5:
                db.add(Interaction(client_id=c.id, agent_id=agent.id, interaction_type=InteractionType.text,
                                   summary="Sent a quick check-in text.", occurred_at=now - timedelta(days=rng.randint(1, 20))))

        db.flush()
        for c in db.scalars(select(Client).where(Client.agent_id.in_(ids))):
            refresh_client_leads(db, c)
        db.commit()
        n = db.scalar(select(func.count(Client.id)).where(Client.agent_id.in_(ids)))
        print(f"Created {n} clients for {', '.join(a.full_name for a in agents)}.")
        print(f"Showcase lead: Aisha Patel (agent: {agents[0].email}) in {showcase_city}.")
        print(f"Agent password: {password}")


if __name__ == "__main__":
    main()
