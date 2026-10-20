# Sign-in and permissions

This page answers the professor's questions about authentication and authorization. The evidence, every endpoint called by every kind of user, is in [security-matrix.md](security-matrix.md).

## How sign-in works

1. The user posts their email and password to `POST /api/auth/login`.
2. The backend checks the password against a bcrypt hash. We never store plain passwords.
3. If it matches, the backend returns a JWT signed with HS256 using `JWT_SECRET`. The token holds the user id, their role and an expiry 60 minutes out.
4. The frontend sends the token as `Authorization: Bearer <token>` on every request.
5. Every protected route depends on `get_current_user`, which rejects a missing, forged or expired token, or a deactivated account, with **401**.

After 5 wrong passwords for the same email within a minute, sign-in is locked for that email for a minute (**429**), even with the right password. In production mode the server refuses to start if `JWT_SECRET` or `ADMIN_PASSWORD` are still the development defaults.

## Who can do what

There are two roles. **Agents** work with their own clients. **Brokers** (admins) manage the team and can see every agent's work.

| Rule | How it's enforced | What an outsider gets |
| --- | --- | --- |
| You must be signed in | `get_current_user` on every route except health and login | 401 |
| Broker-only actions (team management, deleting listings) | `require_roles(UserRole.admin)` dependency | 403 |
| A client, lead, appointment, offer or AI suggestion belongs to one agent | `ensure_owner` on every read and write; lists are filtered by `agent_id` | 404 |

The ownership check returns 404, not 403, on purpose: an agent poking at ids can't even tell whether a record exists.

```python
AdminUser = Annotated[User, Depends(require_roles(UserRole.admin))]   # brokers only, otherwise 403

def ensure_owner(user: User, agent_id: int) -> None:
    if not is_admin(user) and agent_id != user.id:
        raise HTTPException(404, "Not found.")
```

## Can one agent reach another agent's clients by calling the API directly?

No. The security matrix signs in as a second agent and calls all 19 endpoints that read or change another agent's records, including deleting the client, moving the lead, accepting an offer, and asking the AI about the lead. Every one returns 404, and nothing changes. It also checks that the four list endpoints never include another agent's rows.

## How it's tested

`tests/test_security_matrix.py` runs the whole matrix on every push, so CI fails if anyone adds an endpoint and forgets to protect it. The endpoint list comes from the OpenAPI schema, so new endpoints are included automatically. More focused tests cover the lockout, password change and the production-settings check.

## Known limits

We'd rather be upfront about these:

- The sign-in lockout is kept in memory, so it resets when the server restarts. A deployment with several servers would move it to Redis or the database.
- Tokens can't be revoked before they expire; signing out simply discards the token in the browser.
- The token lives in the browser's session storage. React escapes everything it renders, which protects against the usual script-injection route, but an httpOnly cookie would be stronger.
