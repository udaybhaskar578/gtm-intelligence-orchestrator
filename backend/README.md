# GTM Intelligence Backend

FastAPI service that generates AI-powered sales battle cards for Salesforce Account records. Fetches company enrichment from Apollo.io, call intelligence (mocked), and synthesizes everything via GitHub Models (GPT-4.1) into a structured battle card. Results are written back to Salesforce Account fields.

Also includes a Streamlit UI for interactive testing without touching Salesforce directly.

**Deployed on:** AWS Lambda + API Gateway
**Streamlit UI:** Streamlit Community Cloud

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
| `main.py` | Uvicorn entry point (local dev) |
| `lambda_handler.py` | AWS Lambda entry point (Mangum wrapper) |
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

## Local Development

### 1. Create a virtual environment

```bash
cd backend
python3.13 -m venv .venv
source .venv/bin/activate
```

> If `python3.13` is not found: `brew install python@3.13`

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill in your credentials (see [Environment Variables](#environment-variables) below).

### 4. Run the server

```bash
uvicorn main:app --reload --port 8000
```

Verify:
```bash
curl http://localhost:8000/healthz
# {"status":"ok",...}
```

### 5. Run the Streamlit UI (optional)

In a separate terminal:

```bash
source .venv/bin/activate
streamlit run streamlit_app.py
```

Opens at `http://localhost:8501`.

---

## Running Tests

```bash
pytest -q
# or specific files:
pytest tests/test_models.py -v
pytest tests/test_orchestrator.py -v
```

Tests use `USE_APOLLO_REAL_API=false` and `USE_SALESFORCE_WRITE_BACK=false` by default. Only `GITHUB_MODELS_TOKEN` is required. Real LLM calls are mocked via injected fake clients.

---

## AWS Lambda Deployment

The Lambda function is the production entry point. The handler at `lambda_handler.py` wraps the FastAPI app with [Mangum](https://mangum.faramiesolutions.com/).

### First-time setup (run once)

```bash
# 1. Create the IAM execution role
aws iam create-role \
  --role-name gtm-lambda-role \
  --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}'

aws iam attach-role-policy \
  --role-name gtm-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Wait ~10 seconds for IAM to propagate, then:

# 2. Build the Linux-compatible deployment package
cd backend
rm -rf package lambda.zip
python3.13 -m pip install -r requirements-lambda.txt \
  --target ./package \
  --platform manylinux2014_x86_64 \
  --python-version 3.13 \
  --only-binary=:all:

cp -r src package/
cp lambda_handler.py package/
cd package && zip -r ../lambda.zip . -x "*.pyc" -x "*/__pycache__/*" && cd ..

# 3. Create the Lambda function
aws lambda create-function \
  --function-name gtm-intelligence-api \
  --runtime python3.13 \
  --role arn:aws:iam::<YOUR_ACCOUNT_ID>:role/gtm-lambda-role \
  --handler lambda_handler.handler \
  --zip-file "fileb://$(pwd)/lambda.zip" \
  --timeout 60 \
  --memory-size 256 \
  --region us-east-1

# 4. Set environment variables (see Environment Variables section)
aws lambda update-function-configuration \
  --function-name gtm-intelligence-api \
  --region us-east-1 \
  --environment "Variables={PERSIST_OUTPUT=false,OUTPUT_DIR=/tmp/battle_card_results,...}"

# 5. Create API Gateway
aws apigatewayv2 create-api \
  --name gtm-intelligence-api \
  --protocol-type HTTP \
  --region us-east-1

# 6. Wire Lambda to API Gateway (use integration ID from step 5 output)
aws apigatewayv2 create-integration \
  --api-id <API_ID> \
  --integration-type AWS_PROXY \
  --integration-uri arn:aws:lambda:us-east-1:<ACCOUNT_ID>:function:gtm-intelligence-api \
  --payload-format-version 2.0

aws apigatewayv2 create-route \
  --api-id <API_ID> \
  --route-key 'ANY /{proxy+}' \
  --target integrations/<INTEGRATION_ID>

aws apigatewayv2 create-stage \
  --api-id <API_ID> \
  --stage-name '$default' \
  --auto-deploy

aws lambda add-permission \
  --function-name gtm-intelligence-api \
  --statement-id apigateway-invoke \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:us-east-1:<ACCOUNT_ID>:<API_ID>/*"
```

### Redeploy after code changes

```bash
cd backend

# Re-copy source files into the existing package dir and rezip
cp -r src package/
cp lambda_handler.py package/
cd package && zip -r ../lambda.zip . -x "*.pyc" -x "*/__pycache__/*" && cd ..

aws lambda update-function-code \
  --function-name gtm-intelligence-api \
  --zip-file "fileb://$(pwd)/lambda.zip" \
  --region us-east-1
```

### Verify deployment

```bash
curl https://gsmwcf7uy7.execute-api.us-east-1.amazonaws.com/healthz
```

### Important Lambda-specific settings

| Setting | Lambda value | Reason |
|---|---|---|
| `PERSIST_OUTPUT` | `false` | Lambda has no persistent disk at relative paths |
| `OUTPUT_DIR` | `/tmp/battle_card_results` | `/tmp` is the only writable directory (512MB, ephemeral) |
| `STARTUP_PROVIDER_CHECK` | `false` | Avoid cold-start latency from pinging external APIs |
| Timeout | 60 seconds | LLM call can take up to 45s |
| Memory | 256 MB | Sufficient for the Python + pydantic workload |

---

## Streamlit Cloud Deployment

### Deploy

1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub
2. Click **Create app** → **Deploy a public app from GitHub**
3. Fill in:
   - **Repository:** `udaybhaskar578/gtm-intelligence-orchestrator`
   - **Branch:** `main`
   - **Main file path:** `backend/streamlit_app.py`
   - **Python version:** `3.11`
4. Open **Advanced settings → Secrets** and paste all environment variables in TOML format (same keys as `.env`, quoted string values)
5. Click **Deploy**

### Redeploy after code changes

Push to `main` — Streamlit Cloud auto-redeploys on every push to the connected branch.

```bash
git add .
git commit -m "your message"
git push
```

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
| `GITHUB_MODELS_MODEL` | `openai/gpt-4.1` | Model for battle card synthesis |
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

### Salesforce Write-Back

| Variable | Default | Description |
|---|---|---|
| `USE_SALESFORCE_WRITE_BACK` | `true` | Set `false` to skip Salesforce writes |
| `SALESFORCE_CLIENT_ID` | — | Connected App consumer key |
| `SALESFORCE_CLIENT_SECRET` | — | Connected App consumer secret |
| `SALESFORCE_USERNAME` | — | Salesforce login username |
| `SALESFORCE_PASSWORD` | — | Salesforce password |
| `SALESFORCE_SECURITY_TOKEN` | — | Security token appended to password |
| `SALESFORCE_AUTH_BASE_URL` | `https://login.salesforce.com` | Use `https://test.salesforce.com` for sandboxes |
| `SALESFORCE_API_VERSION` | `v61.0` | Salesforce REST API version |
| `SALESFORCE_BATTLE_CARD_FIELD` | `Battle_Card_JSON__c` | Custom field for full JSON blob |
| `SALESFORCE_SUMMARY_FIELD` | `Description` | Standard field for plain-text summary |

### Output and Behavior

| Variable | Default | Description |
|---|---|---|
| `PERSIST_OUTPUT` | `true` | Save each run to `OUTPUT_DIR/<run_id>.json` (set `false` on Lambda) |
| `OUTPUT_DIR` | `output/battle_card_results` | Set to `/tmp/battle_card_results` on Lambda |
| `MOCK_MODE` | `deterministic` | `deterministic` (seeded) or `random` mock data |
| `MOCK_SEED` | `42` | Seed for deterministic mock data |
| `STARTUP_PROVIDER_CHECK` | `false` | Ping external APIs on startup |
| `LOG_LEVEL` | `INFO` | Log verbosity |

---

## API Reference

### GET /healthz

```bash
curl https://gsmwcf7uy7.execute-api.us-east-1.amazonaws.com/healthz
```

### POST /v1/analyze-account

```bash
curl -X POST https://gsmwcf7uy7.execute-api.us-east-1.amazonaws.com/v1/analyze-account \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": "001xx000003DHP1",
    "company_name": "Acme Corp",
    "industry": "Software",
    "domain": "acme.com",
    "write_to_salesforce": false,
    "include_raw_intelligence": false
  }'
```

| Field | Required | Description |
|---|---|---|
| `account_id` | Yes | Salesforce Account ID (15 or 18 chars) |
| `company_name` | Yes | Account name used in LLM prompt |
| `industry` | No | Industry label for enrichment context |
| `domain` | No | Company domain for Apollo enrichment |
| `write_to_salesforce` | No (default `false`) | Whether to PATCH Salesforce Account |
| `include_raw_intelligence` | No (default `false`) | Include raw source data in response |

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

### Lambda: "No module named pydantic_core._pydantic_core"

The package was built on macOS but Lambda runs Linux. Always build with the `--platform` flag:

```bash
python3.13 -m pip install -r requirements-lambda.txt \
  --target ./package \
  --platform manylinux2014_x86_64 \
  --python-version 3.13 \
  --only-binary=:all:
```

### Lambda: Internal Server Error on first invoke

Check CloudWatch logs:
```bash
aws logs tail /aws/lambda/gtm-intelligence-api --since 5m --region us-east-1
```

### Apollo enrichment returns degraded status

- Verify `APOLLO_API_KEY` is valid
- Free tier may not cover all companies — set `USE_APOLLO_REAL_API=false` to use mock data

### Salesforce authentication fails (401)

- Wait 10 minutes after creating a new Connected App
- Confirm `SALESFORCE_SECURITY_TOKEN` is correct (reset it in **Setup → My Personal Information**)
- For sandboxes, use `SALESFORCE_AUTH_BASE_URL=https://test.salesforce.com`

### LLM fallback triggered on every request

- Verify `GITHUB_MODELS_TOKEN` is set and has `models:read` scope
- Confirm `GITHUB_MODELS_MODEL=openai/gpt-4.1` is spelled correctly
- Increase `GITHUB_MODELS_TIMEOUT_SECONDS` if on a slow connection
