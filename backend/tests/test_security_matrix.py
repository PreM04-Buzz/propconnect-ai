"""Runs the full security matrix: every endpoint, every kind of caller.
If someone adds an endpoint and forgets to protect it, this fails."""
from app.scripts import security_report


def test_every_check_in_the_security_matrix_passes():
    checks = security_report.run()
    failed = [f"{c.caller}: {c.method} {c.path} expected {c.expected}, got {c.actual}" for c in checks if not c.passed]
    assert not failed, "\n".join(failed)
    groups = {c.group for c in checks}
    assert {"Sign-in required", "Other agent's records", "Broker only"} <= groups
    # every protected endpoint was tried without a token
    assert sum(c.caller == "no token" for c in checks) >= 36
