# CLAUDE.md — Backend

This file provides guidance to Claude Code when working with code in the `backend/` directory.

## What This Project Does

A FastAPI service that generates AI-powered sales "battle cards" for a given Salesforce account. It fetches company enrichment data and contacts from Apollo.io (real API), call intelligence from Gong (mocked), synthesizes them via GitHub Models (GPT-4.1), and optionally writes results back to Salesforce.

Also includes a Streamlit UI for interactive testing without touching Salesforce directly.

**Production deployments:**
- FastAPI: AWS Lambda + API Gateway — `https://gsmwcf7uy7.execute-api.us-east-1.amazonaws.com`
- Streamlit: Streamlit Community Cloud — `https://udaybhaskar578-gtm-intelligence-orchestrator.streamlit.app`

---

## Commands

### Local dev setup
```bash
cd backend
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in credentials
uvicorn main:app --reload --port 8000
```

### Run Streamlit UI locally
```bash
source .venv/bin/activate
streamlit run streamlit_app.py
```

### Run tests
```bash
pytest
pytest tests/test_models.py -v
pytest tests/test_orchestrator.py -v
```

### Deploy to Lambda (after code changes)
```bash
cd backend
cp -r src package/
cp lambda_handler.py package/
cd package && zip -r ../lambda.zip . -x "*.pyc" -x "*/__pycache__/*" && cd ..
aws lambda update-function-code \
  --function-name gtm-intelligence-api \
  --zip-file "fileb://$(pwd)/lambda.zip" \
  --region us-east-1
```

### Build Lambda package from scratch (cross-platform — must use --platform flag)
```bash
rm -rf package lambda.zip
python3.13 -m pip install -r requirements-lambda.txt \
  --target ./package \
  --platform manylinux2014_x86_64 \
  --python-version 3.13 \
  --only-binary=:all:
cp -r src package/
cp lambda_handler.py package/
cd package && zip -r ../lambda.zip . -x "*.pyc" -x "*/__pycache__/*" && cd ..
```

> Always use `--platform manylinux2014_x86_64 --only-binary=:all:` when building on macOS.
> Lambda runs Amazon Linux — macOS Darwin `.so` files will cause `No module named pydantic_core._pydantic_core`.

---

## Environment Variables

Always required:
- `GITHUB_MODELS_TOKEN` — GitHub PAT with `models:read` scope

Apollo enrichment:
- `USE_APOLLO_REAL_API` — `true` (default) or `false` to use mock data
- `APOLLO_API_KEY` — required when `USE_APOLLO_REAL_API=true`

Salesforce write-back:
- `USE_SALESFORCE_WRITE_BACK` — `true` (default) or `false` to skip
- `SALESFORCE_CLIENT_ID`, `SALESFORCE_CLIENT_SECRET`
- `SALESFORCE_USERNAME`, `SALESFORCE_PASSWORD`, `SALESFORCE_SECURITY_TOKEN`
- `SALESFORCE_AUTH_BASE_URL` — `https://login.salesforce.com` (use `https://test.salesforce.com` for sandboxes)

LLM settings (all have defaults):
- `GITHUB_MODELS_MODEL` — default `openai/gpt-4.1`
- `GITHUB_MODELS_TIMEOUT_SECONDS` — default `45`
- `GITHUB_MODELS_TEMPERATURE` — default `0.2`
- `GITHUB_MODELS_MAX_TOKENS` — default `1400`

Lambda-specific settings:
- `PERSIST_OUTPUT=false` — Lambda has no persistent disk at relative paths
- `OUTPUT_DIR=/tmp/battle_card_results` — only writable directory on Lambda
- `STARTUP_PROVIDER_CHECK=false` — avoid cold-start latency

Other:
- `MOCK_MODE` — `deterministic` (default, seeded) or `random`
- `MOCK_SEED` — integer seed, default `42`
- `SALESFORCE_API_VERSION` — default `v61.0`
- `SALESFORCE_BATTLE_CARD_FIELD` — default `Battle_Card_JSON__c`
- `SALESFORCE_SUMMARY_FIELD` — default `Description`

---

## Architecture

Request lifecycle for `POST /v1/analyze-account`:

1. **`src/api.py`** — FastAPI app. `lifespan` initializes all service clients at startup. Single main endpoint orchestrates the pipeline.

2. **`src/data_sources.py`** — `DataSourceOrchestrator.fetch_all_sources()` fans out concurrently:
   - `ApolloEnrichmentClient` — `GET /organizations/enrich`; falls back to deterministic mock on failure
   - `ApolloContactsClient` — `POST /contacts/search`; falls back to `/mixed_people/api_search`; returns empty when disabled
   - `GongMockDataSource` — deterministic mock call intelligence seeded by company name

3. **`src/orchestrator.py`** — `GTMOrchestrator.synthesize_battle_card()` calls GitHub Models API (via `openai` SDK at custom base URL). Falls back to `_fallback_draft()` on LLM failure or invalid JSON.

4. **`src/salesforce.py`** — `SalesforceClient` authenticates via OAuth password flow and PATCHes the Account. Token cached in-memory; re-authenticates on 401.

5. **`src/settings.py`** — `Settings` (pydantic-settings) loads from `.env`. Field aliases allow multiple env var names. Validates required fields per enabled integration.

6. **`src/models.py`** — All Pydantic models. `BattleCardDraft` is the intermediate LLM output validated before becoming `BattleCard`. `SourceStatus` tracks per-provider success/degraded/failed state.

7. **`src/utils.py`** — `retry_http_request` (exponential backoff), `extract_json_object` (strips markdown fences from LLM output), `coerce_list` / `coerce_int` (normalize Apollo response variations).

8. **`src/logging_config.py`** — Structured logging with `run_id` in every line via `LoggerAdapter`.

**Entry points:**
- `main.py` — Uvicorn entry point for local dev
- `lambda_handler.py` — AWS Lambda entry point (Mangum wrapper around FastAPI app)
- `streamlit_app.py` — Streamlit UI

**Dependency files:**
- `requirements.txt` — full deps including Streamlit and pytest (local dev)
- `requirements-lambda.txt` — Lambda-only deps, excludes Streamlit and pytest (keeps zip small)

---

## Testing Notes

Tests require at minimum `GITHUB_MODELS_TOKEN` set, and `USE_APOLLO_REAL_API=false`, `USE_SALESFORCE_WRITE_BACK=false` unless you have real credentials. `test_orchestrator.py` and `test_api.py` inject fake OpenAI clients to avoid real LLM calls. Uses `pytest-asyncio` for async tests.

---

## Python Version

Use Python 3.11–3.13. Python 3.14 is not supported — `pydantic-core` build fails (`PyO3` max supported version is 3.13). Streamlit Community Cloud is pinned to 3.11 via `.python-version`.
