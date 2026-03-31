# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

A FastAPI service that generates AI-powered sales "battle cards" for a given Salesforce account. It fetches company enrichment data and contact data from Apollo.io (real API), call intelligence from Gong (mocked), then synthesizes them via an LLM (GitHub Models / OpenAI-compatible) into a structured battle card, optionally writing results back to Salesforce.

## Commands

### Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Run the server
```bash
uvicorn main:app --reload
```

### Run all tests
```bash
pytest
```

### Run a single test file
```bash
pytest tests/test_models.py
pytest tests/test_orchestrator.py -v
```

### Run a single test
```bash
pytest tests/test_models.py::test_battle_card_draft_enforces_minimum_items
```

## Environment Variables (`.env`)

Always required:
- `GITHUB_MODELS_TOKEN` — API token for GitHub Models (OpenAI-compatible LLM endpoint)

To run without external APIs (development/testing):
- `USE_APOLLO_REAL_API=false` — skips Apollo enrichment and contacts, uses mock/empty data
- `USE_SALESFORCE_WRITE_BACK=false` — skips Salesforce write-back

When `USE_APOLLO_REAL_API=true` (default):
- `APOLLO_API_KEY` — get one at apollo.io (free tier, accepts personal email)

When `USE_SALESFORCE_WRITE_BACK=true`:
- `SF_CONSUMER_KEY` / `SALESFORCE_CLIENT_ID`
- `SF_CONSUMER_SECRET` / `SALESFORCE_CLIENT_SECRET`
- `SF_USERNAME` / `SALESFORCE_USERNAME`
- `SF_PASSWORD` / `SALESFORCE_PASSWORD`
- `SF_SECURITY_TOKEN` (optional, appended to password)
- `SF_DOMAIN` (optional — `login`, `test`, or custom domain)

Other notable settings with defaults:
- `GITHUB_MODELS_MODEL` — default `openai/gpt-4.1`
- `GITHUB_MODELS_TIMEOUT_SECONDS` — default `45.0`
- `GITHUB_MODELS_TEMPERATURE` — default `0.2`
- `GITHUB_MODELS_MAX_TOKENS` — default `1400`
- `APOLLO_ENRICH_BASE_URL` — default `https://api.apollo.io/api/v1`
- `APOLLO_TIMEOUT_SECONDS` — default `20.0`
- `APOLLO_MAX_RETRIES` — default `2`
- `MOCK_MODE` — `deterministic` (default, seeded by company name) or `random`
- `MOCK_SEED` — integer seed for deterministic mock data, default `42`
- `PERSIST_OUTPUT` — `true` by default; saves `output/battle_card_results/{run_id}.json`
- `STARTUP_PROVIDER_CHECK` — `false` by default; when `true`, pings external endpoints on startup
- `SALESFORCE_API_VERSION` — default `v61.0`
- `SALESFORCE_BATTLE_CARD_FIELD` — Salesforce field for JSON output, default `Battle_Card_JSON__c`
- `SALESFORCE_SUMMARY_FIELD` — Salesforce field for summary text, default `Description`

## Architecture

The request lifecycle for `POST /v1/analyze-account`:

1. **`src/api.py`** — FastAPI app entry point. The `lifespan` context manager initializes all service clients at startup (with optional provider reachability checks) and tears them down on shutdown. The single main endpoint orchestrates the pipeline.

2. **`src/data_sources.py`** — `DataSourceOrchestrator.fetch_all_sources()` fans out concurrently:
   - `ApolloEnrichmentClient` — real `GET /organizations/enrich` call to Apollo.io API; falls back to a deterministic mock if disabled or the call fails. Returns `technology_names`, `keywords`, `estimated_num_employees`, `funding_events`, etc.
   - `ApolloContactsClient` — real `POST /contacts/search` call to Apollo.io API; falls back to `POST /mixed_people/api_search` if the first endpoint fails. Returns empty list when `USE_APOLLO_REAL_API=false`.
   - `GongMockDataSource` — generates deterministic mock call intelligence (seeded by company name)

3. **`src/orchestrator.py`** — `GTMOrchestrator.synthesize_battle_card()` calls the GitHub Models API (via the `openai` SDK pointed at a custom base URL) with a structured JSON prompt. If the LLM fails or returns invalid JSON, it falls back to a `_fallback_draft()` built deterministically from the aggregated intelligence.

4. **`src/salesforce.py`** — `SalesforceClient` authenticates via OAuth password flow and PATCHes the Account record. Token is cached in-memory; re-authenticates once on 401.

5. **`src/settings.py`** — `Settings` (pydantic-settings) loads from `.env`. Field aliases allow multiple env var names (e.g. `SF_CONSUMER_KEY` or `SALESFORCE_CLIENT_ID`). Validation enforces required fields based on which integrations are enabled.

6. **`src/models.py`** — All Pydantic models. `BattleCardDraft` is the intermediate LLM output (validated before becoming a `BattleCard`). `SourceStatus` tracks per-provider success/degraded/failed state.

7. **`src/utils.py`** — `retry_http_request` wraps httpx with exponential backoff. `extract_json_object` strips markdown fences and extracts JSON from LLM output. `coerce_list` / `coerce_int` normalize Apollo API response variations.

8. **`src/logging_config.py`** — `configure_logging()` sets up structured log format including `run_id` in every line. `get_logger(name, run_id)` returns a `LoggerAdapter` used throughout the codebase.

## Testing Notes

Tests require at minimum `GITHUB_MODELS_TOKEN` set (and `USE_APOLLO_REAL_API=false`, `USE_SALESFORCE_WRITE_BACK=false` unless you have real credentials). `test_orchestrator.py` and `test_api.py` inject fake OpenAI clients to avoid real LLM calls. `pytest-asyncio` is used for async tests.
