from app.services import grounding

FACTS = {"client": {"budget_max": "$400,000"},
         "properties_of_interest": [{"address": "48 Maple Ave, Naperville", "price": "$375,000"}],
         "upcoming_appointments": [{"date": "2026-10-24"}]}


def _answer(text):
    return {"summary": text, "recommended_action": "", "reasoning": "", "draft_message": ""}


def test_facts_from_the_data_pass():
    ok, issues = grounding.check(_answer("Book 48 Maple Ave at $375,000, under the $400K budget, on 2026-10-24."), FACTS)
    assert ok, issues


def test_invented_price_is_caught():
    ok, issues = grounding.check(_answer("Offer $350,000 on 48 Maple Ave."), FACTS)
    assert not ok and "$350,000" in issues[0]


def test_invented_address_is_caught():
    ok, issues = grounding.check(_answer("You'll love 12 Lake Shore Dr."), FACTS)
    assert not ok and "12 Lake Shore Dr" in issues[0]


def test_invented_date_is_caught():
    ok, _ = grounding.check(_answer("See you on 2026-11-02."), FACTS)
    assert not ok
