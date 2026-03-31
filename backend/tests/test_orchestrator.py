from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from src.models import (
    AggregatedIntelligence,
    AnalysisRequest,
    CallInsight,
    CompanyIntel,
    Contact,
    SourceStatus,
)
from src.orchestrator import GTMOrchestrator
from src.settings import Settings


class FakeCompletions:
    def __init__(self, content: str):
        self.content = content

    async def create(self, **_kwargs):
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.content))]
        )


class FakeOpenAIClient:
    def __init__(self, content: str):
        self.chat = SimpleNamespace(completions=FakeCompletions(content))

    async def close(self):
        return None


def build_intelligence() -> AggregatedIntelligence:
    return AggregatedIntelligence(
        company_intel=CompanyIntel(
            company_name="Snorkel AI",
            industry="AI/ML",
            employee_count=150,
            technologies=["Python", "Kubernetes"],
            intent_signals=["Hiring ML engineers"],
        ),
        top_contacts=[
            Contact(
                id="1",
                name="Alex Nguyen",
                email="alex@snorkel.ai",
                title="VP Engineering",
                company="Snorkel AI",
            )
        ],
        recent_calls=[
            CallInsight(
                call_id="gong-1",
                duration_minutes=40,
                date="2026-03-20T00:00:00Z",
                participants=["AE", "Buyer"],
                topics=["data quality", "integration"],
                sentiment="positive",
            )
        ],
        raw_data={},
    )


@pytest.mark.asyncio
async def test_synthesize_battle_card_from_valid_model_output():
    response_payload = {
        "company_overview": "Snorkel AI is expanding GTM and prioritizing data quality initiatives.",
        "key_contacts": [
            "Alex Nguyen (VP Engineering)",
            "Jordan Patel (Director Data Platform)",
            "Morgan Kim (Head of MLOps)",
        ],
        "competitive_positioning": "Compete on implementation speed and enterprise controls.",
        "recommended_approach": "Lead with measurable ROI and a short implementation pilot.",
        "talking_points": ["Point A", "Point B", "Point C"],
        "risks_and_objections": ["Risk A", "Risk B"],
        "budget_indicators": "Series B growth profile suggests spend capacity.",
        "next_steps": ["Step A", "Step B"],
    }
    settings = Settings()
    orchestrator = GTMOrchestrator(settings, client=FakeOpenAIClient(json.dumps(response_payload)))

    request = AnalysisRequest(account_id="001xx000003DHP1", company_name="Snorkel AI")
    statuses = {
        "apollo_enrich": SourceStatus(provider="apollo_enrich", status="success", used_mock=False, latency_ms=10),
        "apollo_contacts": SourceStatus(
            provider="apollo_contacts", status="success", used_mock=False, latency_ms=5
        ),
        "gong_mock": SourceStatus(
            provider="gong_mock", status="success", used_mock=True, latency_ms=5
        ),
    }
    card = await orchestrator.synthesize_battle_card(
        request,
        build_intelligence(),
        statuses,
        run_id="test123",
    )
    assert card.account_name == "Snorkel AI"
    assert len(card.talking_points) >= 3
    assert 0 <= card.confidence_score <= 100


@pytest.mark.asyncio
async def test_synthesize_battle_card_falls_back_when_model_output_is_invalid():
    settings = Settings()
    orchestrator = GTMOrchestrator(settings, client=FakeOpenAIClient("not-json"))
    request = AnalysisRequest(account_id="001xx000003DHP1", company_name="Snorkel AI")
    statuses = {
        "apollo_enrich": SourceStatus(provider="apollo_enrich", status="degraded", used_mock=True, latency_ms=10),
        "apollo_contacts": SourceStatus(
            provider="apollo_contacts", status="degraded", used_mock=False, latency_ms=5
        ),
        "gong_mock": SourceStatus(
            provider="gong_mock", status="success", used_mock=True, latency_ms=5
        ),
    }
    card = await orchestrator.synthesize_battle_card(
        request,
        build_intelligence(),
        statuses,
        run_id="test456",
    )
    assert len(card.next_steps) >= 2
    assert "Snorkel AI" in card.company_overview
