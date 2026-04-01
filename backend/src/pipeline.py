from __future__ import annotations

from .data_sources import DataSourceOrchestrator
from .models import AnalysisRequest, AnalyzeAccountResponse, SalesforceWritebackStatus
from .orchestrator import GTMOrchestrator
from .salesforce import SalesforceClient
from .settings import Settings
from .utils import save_json_file


async def run_analysis_pipeline(
    request: AnalysisRequest,
    data_sources: DataSourceOrchestrator,
    orchestrator: GTMOrchestrator,
    salesforce: SalesforceClient,
    run_id: str,
    settings: Settings,
) -> AnalyzeAccountResponse:
    """Run the full GTM enrichment pipeline and return a structured response.

    Handles data fetching, LLM synthesis, optional Salesforce write-back, and
    optional disk persistence. Callers are responsible for closing the service
    clients after this function returns.
    """
    intelligence, source_status = await data_sources.fetch_all_sources(request, run_id=run_id)
    battle_card = await orchestrator.synthesize_battle_card(
        request,
        intelligence,
        source_status,
        run_id=run_id,
    )

    salesforce_status = SalesforceWritebackStatus(
        attempted=False,
        success=False,
        account_id=request.account_id,
        error="Not attempted",
    )
    if request.write_to_salesforce and settings.use_salesforce_write_back:
        salesforce_status = await salesforce.update_account_with_battle_card(
            account_id=request.account_id,
            battle_card=battle_card,
            run_id=run_id,
        )

    response = AnalyzeAccountResponse(
        run_id=run_id,
        battle_card=battle_card,
        source_status=source_status,
        salesforce_writeback=salesforce_status,
        raw_intelligence=intelligence.raw_data if request.include_raw_intelligence else None,
        top_contacts=intelligence.top_contacts,
    )

    if settings.persist_output:
        save_json_file(response.model_dump(mode="json"), settings.output_dir, f"{run_id}.json")

    return response
