from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.models import BattleCard, BattleCardDraft


def test_battle_card_draft_enforces_minimum_items():
    with pytest.raises(ValidationError):
        BattleCardDraft(
            company_overview="A short but meaningful company summary for qualification.",
            key_contacts=["Only One"],
            competitive_positioning="Positioning text that is long enough to pass validation.",
            recommended_approach="Approach text that is long enough to pass validation.",
            talking_points=["Point A", "Point B", "Point C"],
            risks_and_objections=["Risk A", "Risk B"],
            next_steps=["Step A", "Step B"],
        )


def test_battle_card_confidence_bounds():
    with pytest.raises(ValidationError):
        BattleCard(
            account_name="Acme",
            account_id="001xx000003DHP1",
            generated_at=datetime.now(timezone.utc),
            company_overview="Overview",
            key_contacts=["A", "B", "C"],
            competitive_positioning="Positioning",
            recommended_approach="Approach",
            talking_points=["1", "2", "3"],
            risks_and_objections=["R1", "R2"],
            next_steps=["N1", "N2"],
            confidence_score=101,
            data_sources_used=["apollo_enrich"],
        )
