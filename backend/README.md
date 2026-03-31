# GTM Intelligence Backend

A FastAPI service that generates AI-powered sales battle cards for Salesforce Account records. It fetches company enrichment from Apollo.io, call intelligence (mocked), and synthesizes everything via GitHub Models (GPT-4.1) into a structured battle card. Results are written back to Salesforce Account fields.

Also includes a Streamlit UI for interactive testing and review without touching Salesforce directly.

---

## Architecture

```
POST /v1/analyze-account
        |
        +-- Apollo Enrichment (real API)      -> CompanyIntel
        +-- Apollo Contacts Search (real API) -> list[Contact]
        +-- Gong Call Intelligence (mocked)   -> list[CallInsight]
        |
        +-- GTMOrchestrator (GitHub Models / GPT-4.1)
        |       -> BattleCard (validated Pydantic model)
        |
        +-- SalesforceClient (optional PATCH)
        |
        -> AnalyzeAccountResponse (JSON)
```

### Source files

| File | Responsibility |
|---|---|
| `main.py` | Uvicorn entry point |
| `src/api.py` | FastAPI app, lifespan startup, `/v1/analyze-account` route |
| `src/orchestrator.py` | LLM synthesis, fallback logic |
| `src/data_sources.py` | Apollo enrichment + contacts clients, Gong mock |
| `src/salesforce.py` | OAuth password flow + Account PATCH write-back |
| `src/models.py` | All Pydantic models (request, response, battle card, contacts) |
| `src/settings.py` | pydantic-settings config loaded from `.env` |
| `src/utils.py` | HTTP retry helper, JSON extraction, type coercions |
| `src/logging_config.py` | Structured logging with `run_id` context |
| `streamlit_app.py` | Interactive UI for testing enrichment end-to-end |

---

## Prerequisites

- **Python 3.11–3.13** (Python 3.14 is not supported — `pydantic-core` build fails)
- GitHub personal access token with `models:read` scope
- Apollo.io API key (free tier works)
- Salesforce Developer org with a Connected App (for write-back)

---

## Setup

### 1. Create a virtual environment using Python 3.13

```bash
cd backend
python3.13 -m venv .venv
source .venv/bin/activate
```

> If `python3.13` is not found, install it via Homebrew: `brew install python@3.13`

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Create your `.env` file

```bash
cp .env.example .env
```

Then edit `.env` and fill in your credentials (see Environment Variables section below).

---

## Running the Backend Server

```bash
cd backend
source .venv/bin/activate
uvicorn main:app --reload --port 8000
```

The server starts at `http://localhost:8000`.

Verify it is running:

```bash
curl http://localhost:8000/healthz
# Expected: {"status":"ok",...}
```

---

## Running the Streamlit UI

In a separate terminal (keep the backend server running in the first):

```bash
cd backend
source .venv/bin/activate
streamlit run streamlit_app.py
```

The UI opens at `http://localhost:8501`.

**UI flow:**
1. Loads recent Accounts from Salesforce
2. Select an Account from the dropdown
3. Click **Process Account**
4. Displays the synthesized battle card, source status, and structured JSON
5. Saves full output to `output/battle_card_results/<run_id>.json`

> Both the FastAPI server (port 8000) and Streamlit (port 8501) must be running at the same time for the UI to work.

---

## Exposing the Server Publicly (for Salesforce Named Credential)

Salesforce cannot call `localhost`. To connect the Salesforce LWC to this backend, expose it via a public tunnel.

### Using Cloudflare Quick Tunnel (no account required)

```bash
# Install cloudflared
brew install cloudflared

# Start a tunnel pointing to the local backend
cloudflared tunnel --url http://localhost:8000
```

You will see output like:
```
+--------------------------------------------------------------------------------------------+
|  Your quick Tunnel has been created! Visit it at (it may take some time to be reachable):  |
|  https://alternatively-publisher-whatever-fuel.trycloudflare.com                           |
+--------------------------------------------------------------------------------------------+
```

Copy the `https://...trycloudflare.com` URL.

**Then update the Salesforce Named Credential:**
1. In Salesforce Setup, search **Named Credentials**
2. Click **GTM Backend** -> **Edit**
3. Paste the tunnel URL into the **URL** field
4. Save

> The tunnel URL changes every time you restart `cloudflared`. Update the Named Credential any time you restart the tunnel.

---

## Environment Variables

Copy `.env.example` to `.env` and fill in each value.

### Required

| Variable | Description |
|---|---|
| `GITHUB_MODELS_TOKEN` | GitHub PAT with `models:read` scope |

### GitHub Models (LLM)

| Variable | Default | Description |
|---|---|---|
| `GITHUB_MODELS_BASE_URL` | `https://models.github.ai/inference` | OpenAI-compatible endpoint |
| `GITHUB_MODELS_MODEL` | `openai/gpt-4.1` | Model to use for synthesis |
| `GITHUB_MODELS_TIMEOUT_SECONDS` | `45` | Request timeout |
| `GITHUB_MODELS_TEMPERATURE` | `0.2` | Lower = more deterministic output |
| `GITHUB_MODELS_MAX_TOKENS` | `1400` | Max tokens in LLM response |

### Apollo Enrichment

| Variable | Default | Description |
|---|---|---|
| `USE_APOLLO_REAL_API` | `true` | Set `false` to use mock data only |
| `APOLLO_API_KEY` | — | Required when `USE_APOLLO_REAL_API=true` |
| `APOLLO_ENRICH_BASE_URL` | `https://api.apollo.io/api/v1` | Apollo API base |
| `APOLLO_TIMEOUT_SECONDS` | `20` | Per-request timeout |
| `APOLLO_MAX_RETRIES` | `2` | Retry attempts on failure |

> **Apollo note:** `contacts/search` may return empty results for accounts not already in your Apollo contacts on a free plan. `mixed_people/api_search` may require an upgraded plan.

### Salesforce Write-Back

| Variable | Default | Description |
|---|---|---|
| `USE_SALESFORCE_WRITE_BACK` | `true` | Set `false` to skip Salesforce writes |
| `SALESFORCE_CLIENT_ID` | — | Connected App consumer key (also accepts `SF_CONSUMER_KEY`) |
| `SALESFORCE_CLIENT_SECRET` | — | Connected App consumer secret (also accepts `SF_CONSUMER_SECRET`) |
| `SALESFORCE_USERNAME` | — | Salesforce user login (also accepts `SF_USERNAME`) |
| `SALESFORCE_PASSWORD` | — | Salesforce password (also accepts `SF_PASSWORD`) |
| `SALESFORCE_SECURITY_TOKEN` | — | Security token appended to password (also accepts `SF_SECURITY_TOKEN`) |
| `SALESFORCE_AUTH_BASE_URL` | `https://login.salesforce.com` | Use `https://test.salesforce.com` for sandboxes |
| `SALESFORCE_API_VERSION` | `v61.0` | Salesforce REST API version |
| `SALESFORCE_BATTLE_CARD_FIELD` | `Battle_Card_JSON__c` | Custom field for full JSON blob |
| `SALESFORCE_SUMMARY_FIELD` | `Description` | Standard field for plain-text summary |

### Output and Behavior

| Variable | Default | Description |
|---|---|---|
| `PERSIST_OUTPUT` | `true` | Save each run to `output/battle_card_results/<run_id>.json` |
| `OUTPUT_DIR` | `output/battle_card_results` | Directory for persisted run output |
| `MOCK_MODE` | `deterministic` | `deterministic` (seeded) or `random` mock data |
| `MOCK_SEED` | `42` | Seed for deterministic mock data |
| `STARTUP_PROVIDER_CHECK` | `false` | Ping external APIs on startup |
| `LOG_LEVEL` | `INFO` | Log verbosity |

---

## API Reference

### GET /healthz

Returns service health status.

```bash
curl http://localhost:8000/healthz
```

### POST /v1/analyze-account

Generates a battle card for the specified account.

**Request body:**

```json
{
  "account_id": "001xx000003DHP1",
  "company_name": "Acme Corp",
  "industry": "Software",
  "domain": "acme.com",
  "write_to_salesforce": true,
  "include_raw_intelligence": false
}
```

| Field | Required | Description |
|---|---|---|
| `account_id` | Yes | Salesforce Account ID (15 or 18 chars) |
| `company_name` | Yes | Account name used in LLM prompt |
| `industry` | No | Industry label for enrichment context |
| `domain` | No | Company domain for Apollo enrichment |
| `write_to_salesforce` | No (default `false`) | Whether to PATCH Salesforce Account |
| `include_raw_intelligence` | No (default `false`) | Include raw source data in response |

**Response shape:**

```json
{
  "run_id": "a1b2c3d4e5f6",
  "generated_at": "2026-03-31T12:00:00Z",
  "battle_card": {
    "account_name": "Acme Corp",
    "account_id": "001xx000003DHP1",
    "company_overview": "...",
    "competitive_positioning": "...",
    "recommended_approach": "...",
    "talking_points": ["...", "..."],
    "risks_and_objections": ["...", "..."],
    "next_steps": ["...", "..."],
    "confidence_score": 82.0,
    "data_sources_used": ["apollo_enrich", "apollo_contacts", "gong_mock"]
  },
  "top_contacts": [
    {"name": "Jane Smith", "title": "VP Engineering", "email": "...", "phone": "..."}
  ],
  "source_status": {
    "apollo_enrich": {"status": "success", "used_mock": false, "latency_ms": 330},
    "apollo_contacts": {"status": "success", "used_mock": false, "latency_ms": 120},
    "gong_mock": {"status": "success", "used_mock": true, "latency_ms": 2}
  },
  "salesforce_writeback": {
    "attempted": true,
    "success": true,
    "account_id": "001xx000003DHP1",
    "status_code": 204,
    "error": null
  }
}
```

---

## Salesforce Write-Back Fields

When `write_to_salesforce=true` (or triggered via Apex), the service writes these fields on the Account:

| Salesforce Field | Source |
|---|---|
| `Battle_Card_JSON__c` | Full battle card JSON blob |
| `GTM_Company_Overview__c` | `battle_card.company_overview` |
| `GTM_Competitive_Positioning__c` | `battle_card.competitive_positioning` |
| `GTM_Recommended_Approach__c` | `battle_card.recommended_approach` |
| `GTM_Talking_Points__c` | Newline-bulleted talking points |
| `GTM_Risks_Objections__c` | Newline-bulleted risks |
| `GTM_Next_Steps__c` | Newline-bulleted next steps |
| `GTM_Confidence_Score__c` | Numeric score 0-100 |
| `GTM_Last_Enriched__c` | ISO timestamp of enrichment |
| `GTM_Run_ID__c` | `run_id` for tracing |

`GTM_Contacts_JSON__c` is written by Apex (not Python) when triggered from the Salesforce LWC, so the contact data is included in the same DML transaction as the battle card fields.

---

## Salesforce Connected App Setup

1. In Salesforce Setup, search **App Manager** -> **New Connected App**
2. Enable **OAuth Settings**
3. Add OAuth scope: **Full access (full)** (or at minimum: `api`, `refresh_token`)
4. Save and wait ~2-10 minutes for propagation
5. Copy **Consumer Key** -> `SALESFORCE_CLIENT_ID`
6. Copy **Consumer Secret** -> `SALESFORCE_CLIENT_SECRET`
7. Set **Require Secret for Web Server Flow** to true

For Username-Password OAuth to work, the user may need a Security Token. Reset it in **Setup -> My Personal Information -> Reset My Security Token** and append it to the password in `SALESFORCE_SECURITY_TOKEN`.

---

## Running Tests

```bash
cd backend
source .venv/bin/activate
pytest -q
```

Run a specific file:

```bash
pytest tests/test_models.py -v
pytest tests/test_orchestrator.py -v
```

Tests use `USE_APOLLO_REAL_API=false` and `USE_SALESFORCE_WRITE_BACK=false` by default. Only `GITHUB_MODELS_TOKEN` is required. Real LLM calls are mocked via injected fake clients.

---

## Troubleshooting

### "pydantic-core build failed" when installing requirements

Python 3.14 is not supported. Use Python 3.11–3.13:

```bash
brew install python@3.13
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Apollo enrichment returns degraded status

- Verify `APOLLO_API_KEY` is valid
- Verify `APOLLO_ENRICH_BASE_URL` is correct (`https://api.apollo.io/api/v1`)
- Free tier may not have enrichment coverage for all companies
- Set `USE_APOLLO_REAL_API=false` to skip and use mock data

### Salesforce authentication fails (401)

- Verify Connected App is fully provisioned (wait 10 min after creating)
- Check `SALESFORCE_USERNAME` and `SALESFORCE_PASSWORD`
- Confirm `SALESFORCE_SECURITY_TOKEN` is correct (reset it if unsure)
- For sandboxes, set `SALESFORCE_AUTH_BASE_URL=https://test.salesforce.com`

### LLM fallback triggered on every request

The orchestrator falls back to deterministic synthesis if the LLM returns invalid JSON or times out. Check:
- `GITHUB_MODELS_TOKEN` is set and valid
- `GITHUB_MODELS_MODEL` is a valid model name (e.g. `openai/gpt-4.1`)
- `GITHUB_MODELS_TIMEOUT_SECONDS` is high enough (default 45s is usually fine)

### Salesforce Named Credential "404" or timeout from LWC

The Cloudflare tunnel URL changes on every restart of `cloudflared`. Update the Named Credential URL in Salesforce Setup -> Named Credentials -> GTM Backend -> Edit whenever you restart the tunnel.

---

## Development Tips

- Keep `PERSIST_OUTPUT=true` while iterating — each run is saved by `run_id` in `output/battle_card_results/`
- Set `USE_APOLLO_REAL_API=false` and `USE_SALESFORCE_WRITE_BACK=false` for fast local iteration without API calls
- The `MOCK_MODE=deterministic` default means the same company name always produces the same mock data, which is helpful for repeatable tests
