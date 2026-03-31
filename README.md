# ExternalSyncGTM — Salesforce GTM Intelligence Project

This repository contains the Salesforce metadata for the GTM Intelligence integration. It pairs with the Python FastAPI backend in `backend/` to surface AI-generated sales battle cards natively on Salesforce Account records.

## What This Does

- A Quick Action button **"Enrich with GTM AI"** on any Account record triggers an AI enrichment pipeline via the Python backend.
- The backend synthesizes data from Apollo.io and GitHub Models (GPT-4.1) into a structured sales battle card.
- Results are written back to Salesforce and displayed in the **GTM Battle Card** Lightning component on the Account page.
- Sales reps can create Salesforce Contact records directly from enriched contact data with one click.

---

## Repository Structure

```
ExternalSyncGTM/
├── force-app/main/default/
│   ├── classes/
│   │   ├── GTMIntelligenceService.cls          # HTTP callout to Python backend
│   │   └── GTMIntelligenceController.cls       # @AuraEnabled methods for LWC
│   ├── lwc/
│   │   ├── gtmBattleCard/                      # Battle card panel on Account page
│   │   └── gtmEnrichAction/                    # Quick Action modal component
│   ├── objects/Account/fields/
│   │   ├── Battle_Card_JSON__c                 # Full JSON blob from backend
│   │   ├── GTM_Company_Overview__c             # Company overview text
│   │   ├── GTM_Competitive_Positioning__c      # Competitive positioning
│   │   ├── GTM_Recommended_Approach__c         # Recommended sales approach
│   │   ├── GTM_Talking_Points__c               # Bullet-point talking points
│   │   ├── GTM_Risks_Objections__c             # Risks and objections
│   │   ├── GTM_Next_Steps__c                   # Next steps list
│   │   ├── GTM_Confidence_Score__c             # AI confidence score (0-100)
│   │   ├── GTM_Last_Enriched__c                # Timestamp of last enrichment
│   │   ├── GTM_Run_ID__c                       # Backend run ID for tracing
│   │   └── GTM_Contacts_JSON__c                # JSON array of enriched contacts
│   ├── quickActions/
│   │   └── Account.GTM_Enrich.quickAction-meta.xml
│   ├── namedCredentials/
│   │   └── GTM_Backend.namedCredential-meta.xml
│   ├── remoteSiteSettings/
│   │   └── GTM_Backend.remoteSite-meta.xml
│   └── layouts/
│       └── Account-Account Layout.layout-meta.xml
├── backend/                                    # Python FastAPI backend (see backend/README.md)
└── sfdx-project.json
```

---

## Prerequisites

- [Salesforce CLI](https://developer.salesforce.com/tools/salesforcecli) (`sf`) installed
- A Salesforce Developer or Scratch org
- The Python backend running and publicly accessible (see `backend/README.md`)

---

## First-Time Setup

### 1. Authenticate with your Salesforce org

```bash
sf org login web --alias my-org --set-default
```

Or if using a scratch org:

```bash
sf org create scratch --definition-file config/project-scratch-def.json --alias my-org --set-default
```

### 2. Deploy all metadata

```bash
sf project deploy start --source-dir force-app
```

This deploys:
- 11 custom Account fields
- 2 Apex classes
- 2 LWC components
- 1 Quick Action
- Named Credential + Remote Site Setting
- Account page layout (with Quick Action in the action bar)

### 3. Configure the Named Credential URL

After deploying, point the Named Credential at your running Python backend:

1. In Salesforce Setup, search for **Named Credentials**
2. Click **GTM Backend** -> **Edit**
3. Set the **URL** field to your backend's public URL (e.g. a Cloudflare tunnel URL)
4. Save

> **Note:** The Named Credential ships with `http://localhost:8000` as a placeholder. This must be updated to a publicly accessible URL before the Quick Action will work from Salesforce. See `backend/README.md` for how to expose the local server via a public tunnel.

### 4. Add the GTM Battle Card to the Account Record Page

This is a one-time manual step in Lightning App Builder (the FlexiPage template API is not available in Developer Edition orgs):

1. Go to **Setup -> Lightning App Builder**
2. Click **New -> Record Page -> Account**
3. Give it a name (e.g. "Account GTM Page")
4. Drag the **GTM Battle Card** (`c-gtm-battle-card`) component from the component panel onto the page
5. Click **Save** then **Activate**
6. Choose **Assign as Org Default** for Account

---

## Component Behavior

### gtmBattleCard (Account Record Page panel)

| State | What the user sees |
|---|---|
| Not yet enriched | "No enrichment data yet" + **Enrich Account** button |
| Enriching | Loading spinner + status message |
| Enriched | Tabbed battle card: Overview, Strategy, Competitive, Risks, Next Steps, Contacts |

The Contacts tab shows enriched contact cards. Each card has a checkbox. Selecting contacts and clicking **Create Selected** creates linked Salesforce Contact records on the Account.

### gtmEnrichAction (Quick Action modal)

- Triggered from the Account page action bar ("Enrich with GTM AI")
- Immediately calls the backend on open (no extra button click)
- Shows a loading spinner during the ~30-60 second enrichment
- On success: green checkmark + "Enrichment complete! Close to refresh"
- On error: error message + **Retry** button
- Closing the modal triggers a page refresh to show updated battle card data

---

## Apex Classes

### GTMIntelligenceService

Handles the HTTP callout to the Python backend:

- Endpoint: `callout:GTM_Backend/v1/analyze-account`
- Method: `POST`
- Timeout: 120 seconds
- Passes `write_to_salesforce: false` — Apex handles all field writes so `GTM_Contacts_JSON__c` is written in the same DML transaction

### GTMIntelligenceController

`@AuraEnabled` methods consumed by both LWC components:

| Method | Description |
|---|---|
| `triggerEnrichment(accountId)` | Calls backend, writes all GTM fields to Account, returns `{success, run_id, enriched_at}` |
| `getBattleCardData(accountId)` | Cacheable query returning all `GTM_*` fields |
| `createContacts(accountId, contactsJson)` | Parses enriched contact JSON and inserts Contact records |

---

## Redeploying After Changes

```bash
# Deploy everything
sf project deploy start --source-dir force-app

# Deploy only Apex classes
sf project deploy start --source-dir force-app/main/default/classes

# Deploy only LWC
sf project deploy start --source-dir force-app/main/default/lwc

# Check deploy status
sf project deploy report
```

## Retrieving Org Changes Back to Source

```bash
sf project retrieve start --source-dir force-app
```

---

## Troubleshooting

### "Callout loop not allowed" error
Apex is making a callout from a context that already has an open DML transaction. Check that `triggerEnrichment` is called from a fresh async context (the LWC handles this correctly by default).

### Quick Action not appearing on the Account page
Verify the page layout assignment. Go to **Setup -> Object Manager -> Account -> Page Layouts -> Account Layout** and confirm the "Enrich with GTM AI" action is in the **Salesforce Mobile and Lightning Experience Actions** section.

### "Backend returned HTTP 5xx" in the modal
The Python backend is down or the Named Credential URL is stale (Cloudflare tunnel URLs change on restart). Update the Named Credential URL and retry.

### Battle card data not refreshing after enrichment
The `gtmBattleCard` component uses `@wire` with `refreshApex`. If the panel doesn't update, do a full page reload. This can happen if the Quick Action modal closes before the wire refresh completes.

