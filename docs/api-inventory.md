# API inventory

Generated from the code by `python -m app.scripts.api_inventory` on 2026-11-12.

**57 endpoints are implemented.** 52 need a valid sign-in token; the other 5 (health check and login) are public on purpose. 57 have at least one direct automated test, and the security matrix made 245 calls against them (245 passed).

**Who can call it:** *Public* needs no sign-in · *Any signed-in user* needs a valid token · *Own records only* lists only the caller's data · *Owner or broker* returns 404 to any other agent · *Broker only* returns 403 to agents.


## Admin

| Method | Endpoint | What it does | Who can call it | Direct tests | Security checks |
| --- | --- | --- | --- | --- | --- |
| GET | `/api/admin/clients` | Website requests waiting for an agent (default), or every client with their agent. | Broker only | 6 | 5/5 |
| POST | `/api/admin/clients/{client_id}/assign` | Give a client to an agent, or move them to another one. Their leads and upcoming | Broker only | 4 | 5/5 |
| GET | `/api/admin/team` | Everyone on the team, with how much each person is looking after. | Broker only | 2 | 5/5 |

## AI

| Method | Endpoint | What it does | Who can call it | Direct tests | Security checks |
| --- | --- | --- | --- | --- | --- |
| GET | `/api/ai/status` | Ai Status | Any signed-in user | 1 | 4/4 |
| POST | `/api/ai/suggestions/{suggestion_id}/decision` | The agent accepts or dismisses a suggestion. Accepting logs it on the client's timeline. | Owner or broker | 2 | 5/5 |
| POST | `/api/leads/{lead_id}/ai/next-step` | Ask the AI Lead Assistant for the single most useful next step on this lead. | Owner or broker | 13 | 5/5 |
| GET | `/api/leads/{lead_id}/ai/suggestions` | List Suggestions | Owner or broker | 1 | 5/5 |

## Appointments

| Method | Endpoint | What it does | Who can call it | Direct tests | Security checks |
| --- | --- | --- | --- | --- | --- |
| GET | `/api/appointments` | List Appointments | Signed in, own records only | 1 | 5/5 |
| POST | `/api/appointments` | Create Appointment | Owner or broker | 7 | 5/5 |
| PATCH | `/api/appointments/{appointment_id}` | Reschedule or edit notes. Only scheduled appointments can be moved. | Owner or broker | 2 | 5/5 |
| POST | `/api/appointments/{appointment_id}/status` | Complete, cancel or mark a no-show. Completed viewings need feedback and count towards the lead score. | Owner or broker | 4 | 5/5 |

## Auth

| Method | Endpoint | What it does | Who can call it | Direct tests | Security checks |
| --- | --- | --- | --- | --- | --- |
| POST | `/api/auth/login` | OAuth2 password flow. `username` is the user's email. | Public | 7 | – |
| GET | `/api/auth/me` | Me | Any signed-in user | 4 | 4/4 |

## Client portal

| Method | Endpoint | What it does | Who can call it | Direct tests | Security checks |
| --- | --- | --- | --- | --- | --- |
| POST | `/api/portal/accept` | Open the invitation link and choose a password. The link works once. | Public | 9 | – |
| POST | `/api/portal/login` | Portal Login | Public | 6 | – |
| GET | `/api/portal/me` | Everything the client may see about their own search, and nothing about anyone else. | Any signed-in user | 8 | 5/5 |
| GET | `/api/portal/messages` | Portal Messages | Any signed-in user | 1 | 5/5 |
| POST | `/api/portal/messages` | Portal Send | Any signed-in user | 5 | 5/5 |

## Client portal (staff)

| Method | Endpoint | What it does | Who can call it | Direct tests | Security checks |
| --- | --- | --- | --- | --- | --- |
| GET | `/api/clients/{client_id}/portal` | Portal Status | Owner or broker | 1 | 5/5 |
| POST | `/api/clients/{client_id}/portal-invite` | Create (or renew) the client's invitation link. Also works as a password reset. | Owner or broker | 7 | 5/5 |
| GET | `/api/messages/conversations` | Conversations | Any signed-in user | 5 | 4/4 |
| GET | `/api/messages/unread-count` | Unread Count | Any signed-in user | 3 | 4/4 |
| GET | `/api/messages/{client_id}/{channel}` | Staff Thread | Any signed-in user | 3 | 4/4 |
| POST | `/api/messages/{client_id}/{channel}` | Staff Reply | Any signed-in user | 3 | 4/4 |

## Clients

| Method | Endpoint | What it does | Who can call it | Direct tests | Security checks |
| --- | --- | --- | --- | --- | --- |
| GET | `/api/clients` | List Clients | Signed in, own records only | 8 | 5/5 |
| POST | `/api/clients` | Create Client | Any signed-in user | 11 | 4/4 |
| GET | `/api/clients/{client_id}` | Read Client | Owner or broker | 8 | 7/7 |
| PATCH | `/api/clients/{client_id}` | Update Client | Owner or broker | 1 | 5/5 |
| DELETE | `/api/clients/{client_id}` | Delete Client | Owner or broker | 1 | 5/5 |
| POST | `/api/clients/{client_id}/interactions` | Add Interaction | Owner or broker | 1 | 5/5 |
| POST | `/api/clients/{client_id}/interests` | Add Interest | Owner or broker | 4 | 5/5 |
| DELETE | `/api/clients/{client_id}/interests/{interest_id}` | Remove Interest | Owner or broker | 1 | 5/5 |
| GET | `/api/clients/{client_id}/matches` | Client Matches | Owner or broker | 1 | 5/5 |

## Health

| Method | Endpoint | What it does | Who can call it | Direct tests | Security checks |
| --- | --- | --- | --- | --- | --- |
| GET | `/api/health` | Health | Public | 1 | – |

## Leads

| Method | Endpoint | What it does | Who can call it | Direct tests | Security checks |
| --- | --- | --- | --- | --- | --- |
| GET | `/api/leads` | List Leads | Signed in, own records only | 2 | 5/5 |
| POST | `/api/leads` | Create Lead | Owner or broker | 1 | 5/5 |
| GET | `/api/leads/summary` | Stage Summary | Any signed-in user | 1 | 4/4 |
| GET | `/api/leads/{lead_id}` | Read Lead | Owner or broker | 6 | 5/5 |
| PATCH | `/api/leads/{lead_id}` | Update Lead | Owner or broker | 1 | 5/5 |
| POST | `/api/leads/{lead_id}/move` | Move a lead to another pipeline stage. Every move is recorded in the stage history. | Owner or broker | 11 | 5/5 |

## Market

| Method | Endpoint | What it does | Who can call it | Direct tests | Security checks |
| --- | --- | --- | --- | --- | --- |
| GET | `/api/market/my-areas` | The market where your clients want to live (a broker sees every client's area). | Any signed-in user | 2 | 4/4 |
| GET | `/api/market/regions` | Find metro areas by name. With no search, the United States and the Illinois metros. | Any signed-in user | 3 | 4/4 |
| GET | `/api/market/trends` | Monthly homes for sale for up to three areas, with plain-English statistics. | Any signed-in user | 5 | 4/4 |

## Offers

| Method | Endpoint | What it does | Who can call it | Direct tests | Security checks |
| --- | --- | --- | --- | --- | --- |
| GET | `/api/offers` | List Offers | Signed in, own records only | 2 | 5/5 |
| POST | `/api/offers` | Make an offer for a client. Submitting it moves the client's lead to Negotiation. | Owner or broker | 3 | 5/5 |
| POST | `/api/offers/{offer_id}/status` | Move an offer along. Accepting it closes the deal: the lead is Won and the property is sold. | Owner or broker | 2 | 5/5 |

## Properties

| Method | Endpoint | What it does | Who can call it | Direct tests | Security checks |
| --- | --- | --- | --- | --- | --- |
| GET | `/api/properties` | List Properties | Any signed-in user | 3 | 4/4 |
| POST | `/api/properties` | Create Property | Any signed-in user | 2 | 4/4 |
| GET | `/api/properties/cities` | List Cities | Any signed-in user | 1 | 4/4 |
| GET | `/api/properties/{property_id}` | Read Property | Any signed-in user | 3 | 4/4 |
| PATCH | `/api/properties/{property_id}` | Update Property | Any signed-in user | 1 | 4/4 |
| DELETE | `/api/properties/{property_id}` | Delete Property | Broker only | 2 | 5/5 |

## Public

| Method | Endpoint | What it does | Who can call it | Direct tests | Security checks |
| --- | --- | --- | --- | --- | --- |
| POST | `/api/public/intake` | A client describes what they’re looking for. The request waits, unassigned, until the | Public | 18 | – |

## Users

| Method | Endpoint | What it does | Who can call it | Direct tests | Security checks |
| --- | --- | --- | --- | --- | --- |
| GET | `/api/users` | List Users | Broker only | 1 | 5/5 |
| POST | `/api/users` | Brokers/admins create agent accounts; there is no public sign-up. | Broker only | 3 | 5/5 |
| POST | `/api/users/me/password` | Anyone can change their own password, as long as they know the current one. | Any signed-in user | 2 | 4/4 |
| PATCH | `/api/users/{user_id}` | Brokers rename people, change agent and broker roles, and deactivate or reactivate accounts. | Broker only | 7 | 5/5 |
