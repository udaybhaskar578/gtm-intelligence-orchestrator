# CLAUDE.md — GTM Intelligence Orchestrator

This file provides guidance to Claude Code when working with this repository.

## What This Project Does

AI-powered sales battle card generator integrated natively into Salesforce. A button on any Account record triggers an enrichment pipeline (Apollo.io + GPT-4.1) that writes a structured battle card back to 10 custom `GTM_*` fields on the Account.

**Live deployments:**
- Salesforce org: Developer org with all metadata deployed
- FastAPI (Lambda): `https://gsmwcf7uy7.execute-api.us-east-1.amazonaws.com`
- Streamlit UI: `https://udaybhaskar578-gtm-intelligence-orchestrator.streamlit.app`

---

## Repository Structure

```
ExternalSyncGTM/
├── force-app/main/default/
│   ├── classes/            # Apex: GTMIntelligenceService, GTMIntelligenceController (+ tests)
│   ├── lwc/                # LWC: gtmBattleCard, gtmEnrichAction
│   ├── objects/Account/fields/   # 11 custom GTM_* fields
│   ├── quickActions/       # "Enrich with GTM AI" Quick Action
│   ├── namedCredentials/   # GTM_Backend Named Credential (points to Lambda URL)
│   ├── remoteSiteSettings/ # GTM_Backend Remote Site
│   └── permissionsets/     # GTMToolingPermissionSet
├── backend/                # FastAPI + Streamlit (see backend/CLAUDE.md)
└── sfdx-project.json
```

---

## Salesforce Commands

```bash
# Authenticate
sf org login web --alias my-org --set-default

# Deploy everything
sf project deploy start --source-dir force-app

# Deploy only Apex classes
sf project deploy start --source-dir force-app/main/default/classes

# Deploy only LWC
sf project deploy start --source-dir force-app/main/default/lwc

# Pull org changes back to local
sf project retrieve start --source-dir force-app

# Check deploy status
sf project deploy report

# Run Apex tests
sf apex run test --class-names GTMIntelligenceServiceTest --result-format human
sf apex run test --class-names GTMIntelligenceControllerTest --result-format human
```

---

## Salesforce Architecture

### Request flow

```
User clicks "Enrich with GTM AI" Quick Action on Account
        |
gtmEnrichAction LWC  ->  GTMIntelligenceController.triggerEnrichment()
        |
GTMIntelligenceService.enrichAccount()
        |  Named Credential: callout:GTM_Backend
        v
POST /v1/analyze-account  (Lambda)
        |
        +-- Apollo.io enrichment + contacts
        +-- GPT-4.1 synthesis
        v
JSON response  ->  Controller maps fields  ->  Account PATCH (DML)
        |
GTM_* fields updated on Account
        |
gtmBattleCard LWC displays tabbed panel (Overview, Strategy, Competitive, Risks, Next Steps, Contacts)
```

### Apex Classes

**`GTMIntelligenceService`**
- `enrichAccount(accountId, companyName, industry, domain)` — makes the Named Credential callout to `POST /v1/analyze-account` with `write_to_salesforce: false` (Apex handles the DML, not the backend). Returns the raw deserialized JSON map.
- Throws `GTMCalloutException` on HTTP 4xx/5xx.

**`GTMIntelligenceController`** (all `@AuraEnabled`)
- `triggerEnrichment(accountId)` — queries Account fields, calls `GTMIntelligenceService`, maps `battle_card` fields to `GTM_*` Account fields, does DML update, returns `{success, run_id, enriched_at}`.
- `getBattleCardData(accountId)` — cacheable wire method that returns the Account with all `GTM_*` fields for display.
- `createContacts(accountId, contactsJson)` — inserts Contact records from the contacts JSON returned in the battle card.

### LWC Components

**`gtmBattleCard`** — placed on the Account Record Page
- Wires `getBattleCardData` for display
- Calls `triggerEnrichment` on button click, then `refreshApex` to reload
- Parses `GTM_Contacts_JSON__c` for the Contacts tab; allows selecting contacts to create
- Bullet fields (`GTM_Talking_Points__c`, `GTM_Risks_Objections__c`, `GTM_Next_Steps__c`) are stored as `\n• ` delimited strings and split for display

**`gtmEnrichAction`** — Quick Action component (screen action)
- Fires enrichment immediately when the action opens (wires Account Name first)
- Shows loading / success / error states
- Has a Retry button; Close dispatches `CloseActionScreenEvent`

### Custom Account Fields (all prefixed `GTM_`)

| Field | Type | Description |
|---|---|---|
| `GTM_Company_Overview__c` | LongTextArea | company_overview from battle card |
| `GTM_Competitive_Positioning__c` | LongTextArea | competitive_positioning |
| `GTM_Recommended_Approach__c` | LongTextArea | recommended_approach |
| `GTM_Talking_Points__c` | LongTextArea | talking_points (bullet-delimited) |
| `GTM_Risks_Objections__c` | LongTextArea | risks_and_objections (bullet-delimited) |
| `GTM_Next_Steps__c` | LongTextArea | next_steps (bullet-delimited) |
| `GTM_Confidence_Score__c` | Number | confidence_score from LLM |
| `GTM_Last_Enriched__c` | DateTime | timestamp of last enrichment |
| `GTM_Run_ID__c` | Text | run_id UUID for tracing |
| `GTM_Contacts_JSON__c` | LongTextArea | top_contacts raw JSON array |
| `Battle_Card_JSON__c` | LongTextArea | full battle card JSON blob (optional) |

### Named Credential

- Name: `GTM_Backend`
- URL: `https://gsmwcf7uy7.execute-api.us-east-1.amazonaws.com`
- Used in Apex as: `callout:GTM_Backend/v1/analyze-account`
- After deploying, verify/update URL in: Setup → Named Credentials → GTM Backend → Edit

---

## Key Design Decisions

- **`write_to_salesforce: false` in the callout** — Apex does the DML directly rather than delegating to the Python backend. This keeps Salesforce write logic in Apex (governor limits, error handling, transaction control).
- **Bullet-delimited list fields** — `GTM_Talking_Points__c` etc. are stored as plain text with `\n• ` separator. The LWC splits on this to render as a list. Avoids needing a JSON field for simple arrays.
- **Timeout 120s in Apex** — LLM synthesis can take up to 45s; set to 120s to give headroom. Lambda itself has a 60s timeout.
- **`WITH USER_MODE`** — All SOQL queries use `WITH USER_MODE` to respect object/field-level security.

---

## Salesforce Deployment Notes

- Named Credential URL must be updated manually after first deploy (Setup → Named Credentials → GTM Backend)
- The `gtmBattleCard` LWC must be added to the Account Record Page via Lightning App Builder
- Quick Action must be added to the Account page layout or Lightning page
- Connected App for Python write-back (optional) is separate from Named Credential — see `backend/CLAUDE.md`

---

## Python Backend

See [`backend/CLAUDE.md`](backend/CLAUDE.md) for full details on the FastAPI service, Lambda deployment, environment variables, and Streamlit UI.
