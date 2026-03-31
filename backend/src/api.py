from __future__ import annotations

import traceback
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from .data_sources import DataSourceOrchestrator
from .logging_config import configure_logging, get_logger
from .models import AnalysisRequest, AnalyzeAccountResponse, SalesforceWritebackStatus
from .orchestrator import GTMOrchestrator
from .salesforce import SalesforceClient
from .settings import Settings, get_settings
from .utils import save_json_file


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = get_logger(__name__)
    _ensure_output_dir(settings.output_dir)
    _run_startup_checks(settings, logger)
    await _run_provider_reachability_checks(settings, logger)

    app.state.settings = settings
    app.state.data_sources = DataSourceOrchestrator(settings)
    app.state.orchestrator = GTMOrchestrator(settings)
    app.state.salesforce = SalesforceClient(settings)
    logger.info("Application startup complete.")
    try:
        yield
    finally:
        await app.state.data_sources.close()
        await app.state.orchestrator.close()
        await app.state.salesforce.close()
        logger.info("Application shutdown complete.")


app = FastAPI(
    title="GTM Intelligence Orchestrator",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/healthz")
async def healthz(request: Request) -> dict:
    settings: Settings = request.app.state.settings
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": settings.app_name,
        "providers": {
            "apollo_enrich_live": settings.use_apollo_real_api,
            "salesforce_write_back": settings.use_salesforce_write_back,
        },
    }


@app.post("/v1/analyze-account", response_model=AnalyzeAccountResponse)
async def analyze_account(request_body: AnalysisRequest, request: Request) -> AnalyzeAccountResponse:
    run_id = uuid4().hex[:12]
    logger = get_logger(__name__, run_id)
    settings: Settings = request.app.state.settings

    try:
        data_sources: DataSourceOrchestrator = request.app.state.data_sources
        orchestrator: GTMOrchestrator = request.app.state.orchestrator
        salesforce: SalesforceClient = request.app.state.salesforce

        intelligence, source_status = await data_sources.fetch_all_sources(request_body, run_id=run_id)
        battle_card = await orchestrator.synthesize_battle_card(
            request_body,
            intelligence,
            source_status,
            run_id=run_id,
        )

        salesforce_status = SalesforceWritebackStatus(
            attempted=False,
            success=False,
            account_id=request_body.account_id,
            error="Not attempted",
        )
        if request_body.write_to_salesforce and settings.use_salesforce_write_back:
            salesforce_status = await salesforce.update_account_with_battle_card(
                account_id=request_body.account_id,
                battle_card=battle_card,
                run_id=run_id,
            )

        response_payload = AnalyzeAccountResponse(
            run_id=run_id,
            battle_card=battle_card,
            source_status=source_status,
            salesforce_writeback=salesforce_status,
            raw_intelligence=intelligence.raw_data if request_body.include_raw_intelligence else None,
            top_contacts=intelligence.top_contacts,
        )
        _persist_output_if_enabled(settings, response_payload, run_id)
        return response_payload
    except Exception as exc:
        logger.error("Unhandled pipeline failure: %s", exc)
        logger.debug(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail={"message": "Failed to generate battle card", "run_id": run_id, "error": str(exc)},
        ) from exc


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
    return JSONResponse(status_code=exc.status_code, content=detail)


def _ensure_output_dir(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)


def _persist_output_if_enabled(settings: Settings, response: AnalyzeAccountResponse, run_id: str) -> None:
    if not settings.persist_output:
        return
    save_json_file(response.model_dump(mode="json"), settings.output_dir, f"{run_id}.json")


def _run_startup_checks(settings: Settings, logger) -> None:
    logger.info("Running startup checks.")
    if not settings.github_models_base_url.startswith("https://"):
        raise RuntimeError("GITHUB_MODELS_BASE_URL must be a valid https URL.")


async def _run_provider_reachability_checks(settings: Settings, logger) -> None:
    if not settings.startup_provider_check:
        return

    endpoints = {
        "github_models": settings.github_models_base_url,
        "apollo_enrich": settings.apollo_enrich_base_url,
        "salesforce_auth": settings.salesforce_auth_base_url,
    }
    async with httpx.AsyncClient(timeout=8.0) as client:
        for provider, url in endpoints.items():
            try:
                response = await client.get(url)
                logger.info(
                    "Startup provider reachability check passed for %s (status=%s)",
                    provider,
                    response.status_code,
                )
            except Exception as exc:
                logger.warning(
                    "Startup provider reachability check failed for %s (%s): %s",
                    provider,
                    url,
                    exc,
                )
