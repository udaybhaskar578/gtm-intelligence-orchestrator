from __future__ import annotations

import asyncio
import hashlib
import random
from datetime import datetime, timedelta, timezone
from time import perf_counter
from typing import Any, Optional

import httpx

from .logging_config import get_logger
from .models import (
    AggregatedIntelligence,
    AnalysisRequest,
    CallInsight,
    CompanyIntel,
    Contact,
    SourceStatus,
)
from .settings import Settings
from .utils import coerce_int, coerce_list, elapsed_ms, retry_http_request


class ApolloEnrichmentClient:
    """Apollo.io organization enrichment client.

    Docs: https://docs.apollo.io/reference/organization-enrichment
    Endpoint: GET https://api.apollo.io/api/v1/organizations/enrich
    Auth: x-api-key header
    Params: domain, organization_name
    Response fields are top-level (organization object is top-level).
    """

    def __init__(self, settings: Settings, client: Optional[httpx.AsyncClient] = None):
        self.settings = settings
        self.client = client or httpx.AsyncClient(timeout=settings.apollo_timeout_seconds)
        self._owns_client = client is None

    async def close(self) -> None:
        if self._owns_client:
            await self.client.aclose()

    async def enrich_company(
        self, request: AnalysisRequest, *, run_id: str
    ) -> tuple[CompanyIntel, SourceStatus, dict[str, Any]]:
        logger = get_logger(__name__, run_id)
        start = perf_counter()

        if not self.settings.use_apollo_real_api:
            intel = self._fallback_company_intel(request, reason="Apollo enrichment API disabled")
            latency = elapsed_ms(start)
            return (
                intel,
                SourceStatus(
                    provider="apollo_enrich",
                    status="degraded",
                    used_mock=True,
                    latency_ms=latency,
                    error="USE_APOLLO_REAL_API=false",
                ),
                {"fallback_reason": "disabled"},
            )

        url = f"{self.settings.apollo_enrich_base_url.rstrip('/')}/organizations/enrich"
        headers = {"x-api-key": self.settings.apollo_api_key or ""}
        params: dict[str, Any] = {"organization_name": request.company_name}
        if request.domain:
            params["domain"] = request.domain

        try:
            response = await retry_http_request(
                self.client,
                "GET",
                url,
                headers=headers,
                params=params,
                retries=self.settings.apollo_max_retries,
            )
            body = response.json()
            # Apollo wraps the org under an "organization" key
            record = body.get("organization") or body
            intel = self._map_company_intel(request, record)
            latency = elapsed_ms(start)
            logger.info("Apollo enrichment succeeded for %s.", request.company_name)
            return (
                intel,
                SourceStatus(
                    provider="apollo_enrich",
                    status="success",
                    used_mock=False,
                    latency_ms=latency,
                ),
                {"params": params, "response": body},
            )
        except Exception as exc:
            logger.warning("Apollo enrichment failed, using fallback: %s", exc)
            fallback = self._fallback_company_intel(request, reason=str(exc))
            latency = elapsed_ms(start)
            return (
                fallback,
                SourceStatus(
                    provider="apollo_enrich",
                    status="degraded",
                    used_mock=True,
                    latency_ms=latency,
                    error=str(exc)[:300],
                ),
                {"error": str(exc)},
            )

    def _map_company_intel(self, request: AnalysisRequest, record: dict[str, Any]) -> CompanyIntel:
        company_name = record.get("name") or request.company_name
        industry = record.get("industry") or request.industry or "Unknown"

        # Derive latest funding stage and date from funding_events array
        funding_events: list[dict[str, Any]] = record.get("funding_events") or []
        latest_event = funding_events[-1] if funding_events else {}

        revenue = record.get("annual_revenue")

        return CompanyIntel(
            company_name=company_name,
            industry=industry,
            employee_count=coerce_int(record.get("estimated_num_employees"), fallback=0),
            funding_stage=latest_event.get("type"),
            revenue_range=str(revenue) if revenue else None,
            technologies=coerce_list(record.get("technology_names")),
            recent_news=[],
            intent_signals=coerce_list(record.get("keywords")),
            hiring_activity=None,
            recent_funding_round=latest_event.get("date"),
        )

    @staticmethod
    def _fallback_company_intel(request: AnalysisRequest, reason: str) -> CompanyIntel:
        baseline_signals = [
            "No live Apollo enrichment response available",
            "Use discovery call to validate active initiatives",
            f"Fallback generated due to: {reason[:120]}",
        ]
        return CompanyIntel(
            company_name=request.company_name,
            industry=request.industry or "Unknown",
            employee_count=0,
            technologies=[],
            recent_news=[],
            intent_signals=baseline_signals,
            hiring_activity=None,
        )


class GongMockDataSource:
    def __init__(self, settings: Settings):
        self.settings = settings

    def find_calls(self, company_name: str, industry: Optional[str]) -> list[CallInsight]:
        rng = self._rng(company_name, "gong")
        base_topics = {
            "ai": ["data quality", "model drift", "deployment bottlenecks"],
            "finance": ["risk controls", "auditability", "vendor consolidation"],
            "health": ["compliance", "integration timelines", "user adoption"],
        }
        key = self._industry_key(industry)
        topics = base_topics.get(key, ["ROI proof", "team bandwidth", "integration complexity"])
        sentiments = ["positive", "neutral", "negative"]
        results: list[CallInsight] = []

        for index in range(3):
            call_date = datetime.now(timezone.utc) - timedelta(days=(index + 1) * 8)
            call_topics = rng.sample(topics, k=min(2, len(topics)))
            results.append(
                CallInsight(
                    call_id=f"gong-{company_name[:3].lower()}-{index+1}",
                    duration_minutes=rng.randint(28, 54),
                    date=call_date,
                    participants=[
                        "AE",
                        "Solutions Engineer",
                        f"{company_name} stakeholder {index+1}",
                    ],
                    topics=call_topics,
                    sentiment=sentiments[index % len(sentiments)],  # deterministic ordering
                    key_points=[
                        f"Team is evaluating {call_topics[0]} options.",
                        "Decision criteria emphasizes implementation speed.",
                    ],
                    objections_raised=[
                        "Concern about integration complexity",
                        "Need proof of ROI before budget approval",
                    ],
                    next_steps_mentioned="Share tailored case study and run technical workshop.",
                )
            )
        return results

    def _rng(self, company_name: str, namespace: str) -> random.Random:
        if self.settings.mock_mode == "random":
            return random.Random()
        seed_source = f"{namespace}:{company_name}:{self.settings.mock_seed}"
        seed = int(hashlib.sha256(seed_source.encode("utf-8")).hexdigest()[:8], 16)
        return random.Random(seed)

    @staticmethod
    def _industry_key(industry: Optional[str]) -> str:
        if not industry:
            return "default"
        lowered = industry.lower()
        if "ai" in lowered or "machine" in lowered:
            return "ai"
        if "finance" in lowered or "bank" in lowered:
            return "finance"
        if "health" in lowered or "medical" in lowered:
            return "health"
        return "default"


class ApolloContactsClient:
    def __init__(self, settings: Settings, client: Optional[httpx.AsyncClient] = None):
        self.settings = settings
        self.client = client or httpx.AsyncClient(timeout=settings.apollo_timeout_seconds)
        self._owns_client = client is None

    async def close(self) -> None:
        if self._owns_client:
            await self.client.aclose()

    async def search_contacts(
        self,
        *,
        company_name: str,
        domain: Optional[str],
        run_id: str,
        limit: int = 5,
    ) -> tuple[list[Contact], SourceStatus, dict[str, Any]]:
        logger = get_logger(__name__, run_id)
        start = perf_counter()

        if not self.settings.use_apollo_real_api:
            latency = elapsed_ms(start)
            return (
                [],
                SourceStatus(
                    provider="apollo_contacts",
                    status="degraded",
                    used_mock=False,
                    latency_ms=latency,
                    error="USE_APOLLO_REAL_API=false",
                ),
                {"fallback_reason": "disabled"},
            )

        headers = {
            "x-api-key": self.settings.apollo_api_key or "",
            "Content-Type": "application/json",
        }
        safe_limit = max(1, min(limit, 25))
        base_url = self.settings.apollo_enrich_base_url.rstrip("/")

        search_payload = {
            "q_organization_name": company_name,
            "per_page": safe_limit,
            "page": 1,
        }
        if domain:
            search_payload["q_organization_domains"] = [domain]

        contacts_url = f"{base_url}/contacts/search"
        errors: list[str] = []

        try:
            response = await retry_http_request(
                self.client,
                "POST",
                contacts_url,
                headers=headers,
                json=search_payload,
                retries=self.settings.apollo_max_retries,
            )
            body = response.json()
            records = body.get("contacts") or body.get("people") or []
            contacts = self._map_contacts(records, company_name, safe_limit)
            latency = elapsed_ms(start)
            return (
                contacts,
                SourceStatus(
                    provider="apollo_contacts",
                    status="success" if contacts else "degraded",
                    used_mock=False,
                    latency_ms=latency,
                    error=None if contacts else "No contacts returned from /contacts/search",
                ),
                {"endpoint": "/contacts/search", "payload": search_payload, "response": body},
            )
        except Exception as exc:
            errors.append(f"/contacts/search: {exc}")
            logger.warning("Apollo contacts search failed: %s", exc)

        # Fallback to net-new people search for contact-like output.
        people_url = f"{base_url}/mixed_people/api_search"
        people_payload = {"per_page": safe_limit, "page": 1}
        if domain:
            people_payload["q_organization_domains"] = [domain]
        else:
            people_payload["q_organization_name"] = company_name

        try:
            response = await retry_http_request(
                self.client,
                "POST",
                people_url,
                headers=headers,
                json=people_payload,
                retries=self.settings.apollo_max_retries,
            )
            body = response.json()
            records = body.get("people") or body.get("contacts") or []
            contacts = self._map_contacts(records, company_name, safe_limit)
            latency = elapsed_ms(start)
            return (
                contacts,
                SourceStatus(
                    provider="apollo_contacts",
                    status="success" if contacts else "degraded",
                    used_mock=False,
                    latency_ms=latency,
                    error=None if contacts else "No people returned from /mixed_people/api_search",
                ),
                {"endpoint": "/mixed_people/api_search", "payload": people_payload, "response": body},
            )
        except Exception as exc:
            errors.append(f"/mixed_people/api_search: {exc}")
            latency = elapsed_ms(start)
            return (
                [],
                SourceStatus(
                    provider="apollo_contacts",
                    status="failed",
                    used_mock=False,
                    latency_ms=latency,
                    error=" | ".join(errors)[:400],
                ),
                {"errors": errors},
            )

    @staticmethod
    def _map_contacts(records: list[dict[str, Any]], company_name: str, limit: int) -> list[Contact]:
        mapped: list[Contact] = []
        for idx, record in enumerate(records[:limit], start=1):
            first = str(record.get("first_name") or "").strip()
            last = str(record.get("last_name") or "").strip()
            full_name = str(record.get("name") or f"{first} {last}".strip() or "Unknown").strip()
            org_name = (
                record.get("organization_name")
                or (record.get("organization") or {}).get("name")
                or company_name
            )
            title = record.get("title") or "Unknown title"
            email = (
                record.get("email")
                or record.get("email_status")
                or f"unknown{idx}@{company_name.lower().replace(' ', '')}.com"
            )
            linkedin = record.get("linkedin_url") or record.get("linkedin_url_raw")
            mapped.append(
                Contact(
                    id=str(record.get("id") or record.get("contact_id") or f"apollo-contact-{idx}"),
                    name=full_name,
                    email=str(email),
                    title=str(title),
                    company=str(org_name),
                    linkedin_url=str(linkedin) if linkedin else None,
                    phone=str(record.get("phone")) if record.get("phone") else None,
                    seniority=str(record.get("seniority")) if record.get("seniority") else None,
                )
            )
        return mapped


class DataSourceOrchestrator:
    def __init__(
        self,
        settings: Settings,
        apollo_enrich_client: Optional[ApolloEnrichmentClient] = None,
        apollo_contacts_client: Optional[ApolloContactsClient] = None,
        gong_source: Optional[GongMockDataSource] = None,
    ):
        self.settings = settings
        self.apollo_enrich = apollo_enrich_client or ApolloEnrichmentClient(settings)
        self.apollo_contacts = apollo_contacts_client or ApolloContactsClient(settings)
        self.gong = gong_source or GongMockDataSource(settings)

    async def close(self) -> None:
        await self.apollo_enrich.close()
        await self.apollo_contacts.close()

    async def fetch_all_sources(
        self, request: AnalysisRequest, *, run_id: str
    ) -> tuple[AggregatedIntelligence, dict[str, SourceStatus]]:
        logger = get_logger(__name__, run_id)
        enrich_task = asyncio.create_task(self.apollo_enrich.enrich_company(request, run_id=run_id))
        contacts_task = asyncio.create_task(
            self.apollo_contacts.search_contacts(
                company_name=request.company_name,
                domain=request.domain,
                run_id=run_id,
                limit=5,
            )
        )

        gong_start = perf_counter()
        calls = self.gong.find_calls(request.company_name, request.industry)
        gong_status = SourceStatus(
            provider="gong_mock",
            status="success",
            used_mock=True,
            latency_ms=elapsed_ms(gong_start),
        )

        company_intel, enrich_status, enrich_raw = await enrich_task
        contacts, contacts_status, contacts_raw = await contacts_task
        source_status = {
            "apollo_enrich": enrich_status,
            "apollo_contacts": contacts_status,
            "gong_mock": gong_status,
        }

        logger.info(
            "Source fetch complete. apollo_enrich=%s apollo_contacts=%s gong=%s",
            enrich_status.status,
            contacts_status.status,
            gong_status.status,
        )

        intelligence = AggregatedIntelligence(
            company_intel=company_intel,
            top_contacts=contacts,
            recent_calls=calls,
            raw_data={
                "apollo_enrich": enrich_raw,
                "apollo_contacts": contacts_raw,
                "source_status": {
                    key: value.model_dump(mode="json") for key, value in source_status.items()
                },
            },
        )
        return intelligence, source_status
