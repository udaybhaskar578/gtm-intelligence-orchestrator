# GTM Intelligence Orchestrator

AI-powered sales battle card generator integrated natively into Salesforce. Click a button on any Account record to pull enrichment data from Apollo.io, synthesize it through GPT-4.1, and write a structured battle card back to Salesforce — all in under 60 seconds.

---

## Try It Live

**[Launch the Streamlit Demo](https://udaybhaskar578-gtm-intelligence-orchestrator.streamlit.app)**
Run a live enrichment pipeline against any Salesforce account — no setup required.

> To test the full Salesforce integration, reach out to [udaybhaskar578@gmail.com](mailto:udaybhaskar578@gmail.com) for demo credentials.

---

## Live Deployments

| Component | URL |
|---|---|
| Streamlit UI | https://udaybhaskar578-gtm-intelligence-orchestrator.streamlit.app |
| FastAPI (Lambda) | https://gsmwcf7uy7.execute-api.us-east-1.amazonaws.com |

---

## Architecture

```
Salesforce LWC (Account Record Page)
        |
        | Apex callout (Named Credential)
        v
FastAPI on AWS Lambda  (/v1/analyze-account)
        |
        +-- Apollo.io Enrichment API    -> Company intel, funding, tech stack
        +-- Apollo.io Contacts API      -> Key contacts (name, title, email)
        +-- Gong Call Intelligence      -> Call insights (mocked)
        |
        +-- GitHub Models / GPT-4.1     -> Battle card synthesis
        |
        +-- Salesforce REST API         -> Write-back to Account fields
        v
Salesforce Account (GTM_* fields updated)

Streamlit UI (Streamlit Community Cloud)
        |
        +-- Calls same backend services directly (no Lambda)
        +-- For interactive testing and demo without Salesforce
```

---

## Salesforce

### What it does

- A **"Enrich with GTM AI"** Quick Action on any Account record triggers the full enrichment pipeline
- Results are written to 10 custom `GTM_*` fields on the Account
- The **GTM Battle Card** LWC component displays the results in a tabbed panel (Overview, Strategy, Competitive, Risks, Next Steps, Contacts)
- The Contacts tab allows creating linked Salesforce Contact records with one click

### Prerequisites

- [Salesforce CLI](https://developer.salesforce.com/tools/salesforcecli) (`sf`) installed
- A Salesforce Developer or scratch org
- A Connected App in that org (for OAuth write-back from Python)

### Salesforce Connected App Setup

1. In Salesforce Setup, search **App Manager** → **New Connected App**
2. Enable **OAuth Settings**, add scope: **Full access (full)**
3. Save and wait ~10 minutes for propagation
4. Copy **Consumer Key** → use as `SALESFORCE_CLIENT_ID`
5. Copy **Consumer Secret** → use as `SALESFORCE_CLIENT_SECRET`
6. Reset your Security Token: **Setup → My Personal Information → Reset My Security Token**

### Deploy to Salesforce

```bash
# Authenticate
sf org login web --alias my-org --set-default

# Deploy all metadata (fields, Apex, LWC, Named Credential, layouts)
sf project deploy start --source-dir force-app
```

This deploys:
- 11 custom Account fields (`GTM_*`)
- 2 Apex classes (`GTMIntelligenceService`, `GTMIntelligenceController`)
- 2 LWC components (`gtmBattleCard`, `gtmEnrichAction`)
- Named Credential + Remote Site Setting
- Account Quick Action and page layout

### Post-Deploy: Update Named Credential URL

After deploying, point the Named Credential at the live Lambda endpoint:

1. Salesforce Setup → **Named Credentials** → **GTM Backend** → **Edit**
2. Set **URL** to `https://gsmwcf7uy7.execute-api.us-east-1.amazonaws.com`
3. Save

### Add the Battle Card Component to the Account Page

1. Setup → **Lightning App Builder** → **New** → **Record Page** → **Account**
2. Drag the **GTM Battle Card** component onto the page
3. **Save** → **Activate** → **Assign as Org Default**

### Key Salesforce Commands

```bash
# Deploy everything
sf project deploy start --source-dir force-app

# Deploy only Apex
sf project deploy start --source-dir force-app/main/default/classes

# Deploy only LWC
sf project deploy start --source-dir force-app/main/default/lwc

# Pull org changes back to source
sf project retrieve start --source-dir force-app

# Check deploy status
sf project deploy report

# Run Apex tests
sf apex run test --class-names GTMIntelligenceServiceTest --result-format human
```

---

## Python Backend

FastAPI service that runs the enrichment pipeline. Deployed on AWS Lambda, also runnable locally.

See [`backend/README.md`](backend/README.md) for full environment variable reference, API docs, and local dev setup.

### Prerequisites

- Python 3.11–3.13 (3.14 is not supported — `pydantic-core` build fails)
- AWS CLI configured (`aws configure`)
- Apollo.io API key — free tier works, sign up at apollo.io
- GitHub personal access token with `models:read` scope

### Apollo.io API Key Setup

1. Go to [apollo.io](https://www.apollo.io) and create a free account (personal email works)
2. Navigate to **Settings → Integrations → API**
3. Click **Create new key**
4. Copy the key → use as `APOLLO_API_KEY`

> Free tier provides enrichment for most companies and limited contact searches. `contacts/search` may return empty for accounts not in your Apollo network.

### GitHub Models API Token Setup

GitHub Models gives free access to GPT-4.1 and other models via an OpenAI-compatible endpoint.

1. Go to [github.com/settings/tokens](https://github.com/settings/tokens)
2. **Generate new token (classic)**
3. Select scope: **`models:read`** (under the Models section, or just `repo` covers it)
4. Copy the token → use as `GITHUB_MODELS_TOKEN`

> The endpoint is `https://models.github.ai/inference` and the model is `openai/gpt-4.1`. No billing required on the free tier.

### Local Development

```bash
cd backend
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your keys
uvicorn main:app --reload --port 8000
```

Verify:
```bash
curl http://localhost:8000/healthz
```

### AWS Lambda Deployment

#### One-time AWS setup

1. [Create an AWS account](https://aws.amazon.com/free) — free tier includes 1M Lambda requests/month forever
2. In **IAM → Users**, create a user named `cli-deploy` with **AdministratorAccess**
3. Under that user's **Security credentials**, create an access key (CLI type)
4. Configure the CLI:

```bash
aws configure
# Access Key ID:     <your key>
# Secret Access Key: <your secret>
# Default region:    us-east-1
# Output format:     json
```

#### Build and deploy

```bash
cd backend

# Build Linux-compatible package (must use --platform flag — Lambda runs Linux)
rm -rf package lambda.zip
python3.13 -m pip install -r requirements-lambda.txt \
  --target ./package \
  --platform manylinux2014_x86_64 \
  --python-version 3.13 \
  --only-binary=:all:

cp -r src package/
cp lambda_handler.py package/
cd package && zip -r ../lambda.zip . -x "*.pyc" -x "*/__pycache__/*" && cd ..

# Deploy
aws lambda update-function-code \
  --function-name gtm-intelligence-api \
  --zip-file "fileb://$(pwd)/lambda.zip" \
  --region us-east-1
```

> First-time deploy? The IAM role and Lambda function must be created first. See [`backend/README.md`](backend/README.md) for the full first-time setup steps.

#### Redeploy after code changes

```bash
cd backend
cd package && zip -r ../lambda.zip . -x "*.pyc" -x "*/__pycache__/*" && cd ..
aws lambda update-function-code \
  --function-name gtm-intelligence-api \
  --zip-file "fileb://$(pwd)/lambda.zip" \
  --region us-east-1
```

#### Verify

```bash
curl https://gsmwcf7uy7.execute-api.us-east-1.amazonaws.com/healthz
```

---

## Streamlit UI

Interactive frontend for testing the enrichment pipeline without touching Salesforce. Deployed on Streamlit Community Cloud.

**Live:** https://udaybhaskar578-gtm-intelligence-orchestrator.streamlit.app

### What it does

1. Loads Salesforce Accounts from your org
2. Select an Account from the dropdown
3. Click **Process Account** to run the full enrichment pipeline
4. Displays the synthesized battle card, source status, and structured JSON
5. Writes results back to Salesforce (same as the LWC flow)

### Run locally

```bash
cd backend
source .venv/bin/activate
streamlit run streamlit_app.py
```

Opens at `http://localhost:8501`. Requires the same `.env` variables as the backend.

### Deploy to Streamlit Community Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub
2. Click **Create app** → **Deploy a public app from GitHub**
3. Fill in:
   - **Repository:** `udaybhaskar578/gtm-intelligence-orchestrator`
   - **Branch:** `main`
   - **Main file path:** `backend/streamlit_app.py`
   - **Python version:** `3.11`
4. Open **Advanced settings → Secrets** and paste your environment variables in TOML format:

```toml
GITHUB_MODELS_TOKEN = "github_pat_..."
GITHUB_MODELS_BASE_URL = "https://models.github.ai/inference"
GITHUB_MODELS_MODEL = "openai/gpt-4.1"
GITHUB_MODELS_TIMEOUT_SECONDS = "45"
GITHUB_MODELS_TEMPERATURE = "0.2"
GITHUB_MODELS_MAX_TOKENS = "1400"
USE_APOLLO_REAL_API = "true"
APOLLO_API_KEY = "..."
APOLLO_ENRICH_BASE_URL = "https://api.apollo.io/api/v1"
APOLLO_TIMEOUT_SECONDS = "20"
APOLLO_MAX_RETRIES = "2"
MOCK_MODE = "deterministic"
MOCK_SEED = "42"
USE_SALESFORCE_WRITE_BACK = "true"
SALESFORCE_AUTH_BASE_URL = "https://login.salesforce.com"
SALESFORCE_API_VERSION = "v61.0"
SALESFORCE_CLIENT_ID = "..."
SALESFORCE_CLIENT_SECRET = "..."
SALESFORCE_USERNAME = "..."
SALESFORCE_PASSWORD = "..."
SALESFORCE_SECURITY_TOKEN = "..."
SALESFORCE_BATTLE_CARD_FIELD = "Battle_Card_JSON__c"
SALESFORCE_SUMMARY_FIELD = "Description"
PERSIST_OUTPUT = "false"
```

5. Click **Deploy**

> Streamlit Cloud reads secrets as environment variables, so `pydantic-settings` picks them up automatically — no code changes needed.

---

## Repository Structure

```
ExternalSyncGTM/
├── force-app/main/default/
│   ├── classes/                        # Apex: GTMIntelligenceService, GTMIntelligenceController
│   ├── lwc/                            # LWC: gtmBattleCard, gtmEnrichAction
│   ├── objects/Account/fields/         # 11 custom GTM_* fields
│   ├── quickActions/                   # "Enrich with GTM AI" Quick Action
│   ├── namedCredentials/               # GTM_Backend Named Credential
│   ├── remoteSiteSettings/             # GTM_Backend Remote Site
│   └── permissionsets/                 # GTMToolingPermissionSet
├── backend/
│   ├── src/                            # FastAPI app source (api, orchestrator, models, etc.)
│   ├── streamlit_app.py                # Streamlit UI
│   ├── lambda_handler.py               # AWS Lambda entry point (Mangum wrapper)
│   ├── main.py                         # Uvicorn entry point for local dev
│   ├── requirements.txt                # Full deps (includes Streamlit, for local dev)
│   ├── requirements-lambda.txt         # Lambda-only deps (no Streamlit/pytest)
│   ├── .python-version                 # Pins Python 3.11 for Streamlit Cloud
│   └── .streamlit/config.toml          # Streamlit Cloud server config
└── sfdx-project.json
```
