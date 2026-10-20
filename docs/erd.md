# Database: entity relationship diagram

Eleven tables. GitHub draws the diagram below automatically. Timestamps (`created_at`, `updated_at`) are on every table except `lead_stage_history` and `market_inventory`, and are left out to keep the picture readable.

```mermaid
erDiagram
  USERS ||--o{ CLIENTS : manages
  USERS ||--o{ LEADS : owns
  CLIENTS ||--o{ LEADS : has
  LEADS ||--o{ LEAD_STAGE_HISTORY : records
  USERS ||--o{ LEAD_STAGE_HISTORY : changed_by
  CLIENTS ||--o{ PROPERTY_INTERESTS : shortlists
  PROPERTIES ||--o{ PROPERTY_INTERESTS : on
  CLIENTS ||--o{ INTERACTIONS : has
  USERS ||--o{ INTERACTIONS : logs
  USERS ||--o{ APPOINTMENTS : schedules
  CLIENTS ||--o{ APPOINTMENTS : attends
  PROPERTIES |o--o{ APPOINTMENTS : viewed_in
  CLIENTS ||--o{ OFFERS : makes
  PROPERTIES ||--o{ OFFERS : receives
  LEADS |o--o{ OFFERS : moves
  LEADS ||--o{ AI_SUGGESTIONS : gets
  CLIENTS ||--o{ AI_SUGGESTIONS : about
  USERS ||--o{ AI_SUGGESTIONS : decided_by

  USERS { int id PK
    string email UK
    string full_name
    string hashed_password
    string role "agent or admin"
    bool is_active }
  CLIENTS { int id PK
    int agent_id FK
    string first_name
    string last_name
    string email
    string phone
    string client_type
    decimal budget_min
    decimal budget_max
    bool budget_confirmed
    string preferred_city
    int min_bedrooms
    decimal min_bathrooms
    string financing_status
    int purchase_timeline_months
    text notes }
  LEADS { int id PK
    int client_id FK
    int agent_id FK
    string stage "new to won or lost"
    string source
    int score "0 to 100"
    string priority
    string lost_reason }
  LEAD_STAGE_HISTORY { int id PK
    int lead_id FK
    string from_stage
    string to_stage
    int changed_by_id FK
    datetime changed_at }
  PROPERTIES { int id PK
    string status "for_sale, sold"
    decimal price
    int bedrooms
    decimal bathrooms
    int house_size_sqft
    string street_address
    string city
    string zip_code
    date prev_sold_date }
  PROPERTY_INTERESTS { int id PK
    int client_id FK
    int property_id FK
    string interest_level }
  INTERACTIONS { int id PK
    int client_id FK
    int agent_id FK
    string interaction_type
    text summary
    datetime occurred_at }
  APPOINTMENTS { int id PK
    int agent_id FK
    int client_id FK
    int property_id FK "optional"
    string appointment_type
    string status
    datetime starts_at
    datetime ends_at
    text outcome }
  OFFERS { int id PK
    int client_id FK
    int property_id FK
    int lead_id FK "optional"
    decimal amount
    decimal counter_amount
    string status
    datetime submitted_at
    datetime decided_at }
  AI_SUGGESTIONS { int id PK
    int lead_id FK
    int client_id FK
    int agent_id FK
    string source "openai or rules"
    string model
    string prompt_version
    bool grounded
    string action_type
    text recommended_action
    text draft_message
    string status "suggested, accepted, dismissed" }
  MARKET_INVENTORY { int id PK
    int region_id
    string region_name
    date month
    int inventory }
```

`market_inventory` stands alone on purpose: the Zillow data has no key that joins to individual listings. Each region has one row per month.
