from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import streamlit as st

from src.data_sources import DataSourceOrchestrator
from src.models import AnalysisRequest
from src.orchestrator import GTMOrchestrator
from src.salesforce import SalesforceClient
from src.settings import get_settings
from src.utils import save_json_file


st.set_page_config(page_title="GTM Orchestrator", page_icon=":bar_chart:", layout="wide")
st.title("GTM Intelligence Orchestrator")
st.caption("Select a Salesforce Account, process enrichment + battle card, write back, and review output.")


def _run_async(coro):
    return asyncio.run(coro)


def _domain_from_website(website: str | None) -> str | None:
    if not website:
        return None
    raw = website.strip()
    if not raw:
        return None
    if not raw.startswith(("http://", "https://")):
        raw = f"https://{raw}"
    parsed = urlparse(raw)
    host = parsed.netloc.lower().strip()
    if host.startswith("www."):
        host = host[4:]
    return host or None


async def _fetch_accounts(limit: int) -> list[dict]:
    settings = get_settings()
    sf = SalesforceClient(settings)
    try:
        return await sf.list_accounts(run_id="ui_list_accounts", limit=limit)
    finally:
        await sf.close()


async def _process_account(account: dict) -> dict:
    settings = get_settings()
    run_id = f"ui_{uuid4().hex[:10]}"

    request = AnalysisRequest(
        account_id=account["Id"],
        company_name=account.get("Name") or "Unknown Account",
        industry=account.get("Industry"),
        domain=_domain_from_website(account.get("Website")),
        write_to_salesforce=True,
        include_raw_intelligence=True,
    )

    ds = DataSourceOrchestrator(settings)
    orch = GTMOrchestrator(settings)
    sf = SalesforceClient(settings)
    try:
        intelligence, source_status = await ds.fetch_all_sources(request, run_id=run_id)
        battle_card = await orch.synthesize_battle_card(
            request,
            intelligence,
            source_status,
            run_id=run_id,
        )
        readable_md = await orch.format_battle_card_markdown(battle_card, run_id=run_id)
        writeback = await sf.update_account_with_battle_card(
            account_id=request.account_id,
            battle_card=battle_card,
            run_id=run_id,
        )

        payload = {
            "run_id": run_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "request": request.model_dump(mode="json"),
            "source_status": {
                key: value.model_dump(mode="json") for key, value in source_status.items()
            },
            "battle_card": battle_card.model_dump(mode="json"),
            "readable_markdown": readable_md,
            "salesforce_writeback": writeback.model_dump(mode="json"),
            "raw_intelligence": intelligence.raw_data,
        }
        output_path = save_json_file(
            payload,
            Path(settings.output_dir),
            f"streamlit_{request.account_id}_{run_id}.json",
        )
        payload["output_file"] = str(output_path.resolve())
        return payload
    finally:
        await ds.close()
        await orch.close()
        await sf.close()


with st.sidebar:
    st.header("Controls")
    account_limit = st.slider("Accounts to load", min_value=10, max_value=200, value=50, step=10)
    if st.button("Refresh Account List"):
        st.session_state.pop("accounts", None)
        st.session_state.pop("selected_account_id", None)


if "accounts" not in st.session_state:
    with st.spinner("Loading accounts from Salesforce..."):
        st.session_state["accounts"] = _run_async(_fetch_accounts(account_limit))

accounts: list[dict] = st.session_state.get("accounts", [])
if not accounts:
    st.error("No accounts returned from Salesforce. Check your org access and try refresh.")
    st.stop()

account_map = {acct["Id"]: acct for acct in accounts if acct.get("Id")}
options = list(account_map.keys())

selected_id = st.selectbox(
    "Select Salesforce Account",
    options=options,
    format_func=lambda account_id: (
        f"{account_map[account_id].get('Name', 'Unknown')} ({account_id})"
    ),
)
st.session_state["selected_account_id"] = selected_id
selected_account = account_map[selected_id]

left, right = st.columns(2)
with left:
    st.write("**Industry**:", selected_account.get("Industry") or "N/A")
with right:
    st.write("**Website**:", selected_account.get("Website") or "N/A")

if st.button("Process Account", type="primary"):
    with st.spinner("Running Apollo enrichment, GPT synthesis, and Salesforce write-back..."):
        result = _run_async(_process_account(selected_account))
    st.session_state["last_result"] = result

if "last_result" in st.session_state:
    result = st.session_state["last_result"]
    st.subheader("Execution Result")
    st.write(f"**Run ID:** `{result['run_id']}`")
    st.write(f"**Output File:** `{result['output_file']}`")

    writeback = result["salesforce_writeback"]
    if writeback["success"]:
        st.success(f"Salesforce write-back succeeded (status code {writeback['status_code']}).")
    else:
        st.error(
            "Salesforce write-back failed: "
            f"{writeback.get('error') or 'unknown error'}"
        )

    st.subheader("Readable Battle Card")
    st.markdown(result["readable_markdown"])

    with st.expander("Source Status"):
        st.json(result["source_status"])

    with st.expander("Structured Battle Card JSON"):
        st.json(result["battle_card"])
