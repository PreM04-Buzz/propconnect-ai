# API inventory

Generated from the code by `python -m app.scripts.api_inventory` on 2026-10-20.

**38 endpoints are implemented.** 36 need a valid sign-in token; the other 2 (health check and login) are public on purpose. 38 have at least one direct automated test, and the security matrix made 136 calls against them (136 passed).

**Who can call it:** *Public* needs no sign-in · *Any signed-in user* needs a valid token · *Own records only* lists only the caller's data · *Owner or broker* returns 404 to any other agent · *Broker only* returns 403 to agents.


## AI

| Method | Endpoint | What it does | Who can call it | Direct tests | Security checks |
| --- | --- | --- | --- | --- | --- |
| GET | `/api/ai/status` | Ai Status | Any signed-in user | 1 | 3/3 |
| POST | `/api/ai/suggestions/{suggestion_id}/decision` | The agent accepts or dismisses a suggestion. Accepting logs it on the client's timeline. | Owner or broker | 2 | 4/4 |
| POST | `/api/leads/{lead_id}/ai/next-step` | Ask the AI Lead Assistant for the single most useful next step on this lead. | Owner or broker | 11 | 4/4 |
| GET | `/api/leads/{lead_id}/ai/suggestions` | List Suggestions | Owner or broker | 1 | 4/4 |

## Appointments

| Method | Endpoint | What it does | Who can call it | Direct tests | Security checks |
| --- | --- | --- | --- | --- | --- |
| GET | `/api/appointments` | List Appointments | Signed in, own records only | 1 | 4/4 |
| POST | `/api/appointments` | Create Appointment | Owner or broker | 2 | 4/4 |
| PATCH | `/api/appointments/{appointment_id}` | Reschedule or edit notes. Only scheduled appointments can be moved. | Owner or broker | 2 | 4/4 |
| POST | `/api/appointments/{appointment_id}/status` | Complete, cancel or mark a no-show. Completed viewings need feedback and count towards the lead score. | Owner or broker | 4 | 4/4 |

## Auth

| Method | Endpoint | What it does | Who can call it | Direct tests | Security checks |
| --- | --- | --- | --- | --- | --- |
| POST | `/api/auth/login` | OAuth2 password flow. `username` is the user's email. | Public | 6 | – |
| GET | `/api/auth/me` | Me | Any signed-in user | 3 | 3/3 |

## Clients

| Method | Endpoint | What it does | Who can call it | Direct tests | Security checks |
| --- | --- | --- | --- | --- | --- |
| GET | `/api/clients` | List Clients | Signed in, own records only | 4 | 4/4 |
| POST | `/api/clients` | Create Client | Any signed-in user | 10 | 3/3 |
| GET | `/api/clients/{client_id}` | Read Client | Owner or broker | 5 | 6/6 |
| PATCH | `/api/clients/{client_id}` | Update Client | Owner or broker | 1 | 4/4 |
| DELETE | `/api/clients/{client_id}` | Delete Client | Owner or broker | 1 | 4/4 |
| POST | `/api/clients/{client_id}/interactions` | Add Interaction | Owner or broker | 1 | 4/4 |
| POST | `/api/clients/{client_id}/interests` | Add Interest | Owner or broker | 4 | 4/4 |
| DELETE | `/api/clients/{client_id}/interests/{interest_id}` | Remove Interest | Owner or broker | 1 | 4/4 |
| GET | `/api/clients/{client_id}/matches` | Client Matches | Owner or broker | 1 | 4/4 |

## Health

| Method | Endpoint | What it does | Who can call it | Direct tests | Security checks |
| --- | --- | --- | --- | --- | --- |
| GET | `/api/health` | Health | Public | 1 | – |

## Leads

| Method | Endpoint | What it does | Who can call it | Direct tests | Security checks |
| --- | --- | --- | --- | --- | --- |
| GET | `/api/leads` | List Leads | Signed in, own records only | 2 | 4/4 |
| POST | `/api/leads` | Create Lead | Owner or broker | 1 | 4/4 |
| GET | `/api/leads/summary` | Stage Summary | Any signed-in user | 1 | 3/3 |
| GET | `/api/leads/{lead_id}` | Read Lead | Owner or broker | 6 | 4/4 |
| PATCH | `/api/leads/{lead_id}` | Update Lead | Owner or broker | 1 | 4/4 |
| POST | `/api/leads/{lead_id}/move` | Move a lead to another pipeline stage. Every move is recorded in the stage history. | Owner or broker | 8 | 4/4 |

## Offers

| Method | Endpoint | What it does | Who can call it | Direct tests | Security checks |
| --- | --- | --- | --- | --- | --- |
| GET | `/api/offers` | List Offers | Signed in, own records only | 2 | 4/4 |
| POST | `/api/offers` | Make an offer for a client. Submitting it moves the client's lead to Negotiation. | Owner or broker | 2 | 4/4 |
| POST | `/api/offers/{offer_id}/status` | Move an offer along. Accepting it closes the deal: the lead is Won and the property is sold. | Owner or broker | 2 | 4/4 |

## Properties

| Method | Endpoint | What it does | Who can call it | Direct tests | Security checks |
| --- | --- | --- | --- | --- | --- |
| GET | `/api/properties` | List Properties | Any signed-in user | 3 | 3/3 |
| POST | `/api/properties` | Create Property | Any signed-in user | 2 | 3/3 |
| GET | `/api/properties/cities` | List Cities | Any signed-in user | 1 | 3/3 |
| GET | `/api/properties/{property_id}` | Read Property | Any signed-in user | 3 | 3/3 |
| PATCH | `/api/properties/{property_id}` | Update Property | Any signed-in user | 1 | 3/3 |
| DELETE | `/api/properties/{property_id}` | Delete Property | Broker only | 2 | 4/4 |

## Users

| Method | Endpoint | What it does | Who can call it | Direct tests | Security checks |
| --- | --- | --- | --- | --- | --- |
| GET | `/api/users` | List Users | Broker only | 1 | 4/4 |
| POST | `/api/users` | Brokers/admins create agent accounts; there is no public sign-up. | Broker only | 2 | 4/4 |
| POST | `/api/users/me/password` | Anyone can change their own password, as long as they know the current one. | Any signed-in user | 2 | 3/3 |
