from __future__ import annotations

import json
from types import SimpleNamespace

from fastapi.testclient import TestClient

from src.api import app


class FakeCompletions:
    async def create(self, **_kwargs):
        content = json.dumps(
            {
                "company_overview": "Acme is focused on operational efficiency and predictable growth.",
                "key_contacts": [
                    "Alex Nguyen (VP Ops)",
                    "Jordan Patel (Director Engineering)",
                    "Taylor Kim (Head of Analytics)",
                ],
                "competitive_positioning": "Differentiate on speed to value and lower integration risk.",
                "recommended_approach": "Lead with quick wins and clear proof-of-value milestones.",
                "talking_points": ["A", "B", "C"],
                "risks_and_objections": ["R1", "R2"],
                "budget_indicators": "Recent hiring suggests active investment.",
                "next_steps": ["N1", "N2"],
            }
        )
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


class FakeOpenAIClient:
    def __init__(self):
        self.chat = SimpleNamespace(completions=FakeCompletions())

    async def close(self):
        return None


def test_analyze_account_endpoint_returns_structured_payload():
    with TestClient(app) as client:
        client.app.state.orchestrator.client = FakeOpenAIClient()
        client.app.state.orchestrator._owns_client = False

        response = client.post(
            "/v1/analyze-account",
            json={
                "account_id": "001xx000003DHP1",
                "company_name": "Acme Corp",
                "industry": "AI/ML",
                "write_to_salesforce": False,
                "include_raw_intelligence": True,
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert "run_id" in body
        assert body["battle_card"]["account_name"] == "Acme Corp"
        assert "apollo_enrich" in body["source_status"]
        assert body["salesforce_writeback"]["attempted"] is False
