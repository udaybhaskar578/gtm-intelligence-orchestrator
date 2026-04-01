from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class BattleCardDraft(BaseModel):
    company_overview: str = Field(..., min_length=20)
    key_contacts: list[str] = Field(..., min_length=3, max_length=7)
    competitive_positioning: str = Field(..., min_length=20)
    recommended_approach: str = Field(..., min_length=20)
    talking_points: list[str] = Field(..., min_length=3, max_length=8)
    risks_and_objections: list[str] = Field(..., min_length=2, max_length=8)
    budget_indicators: Optional[str] = None
    next_steps: list[str] = Field(..., min_length=2, max_length=8)


class BattleCard(BaseModel):
    account_name: str
    account_id: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    company_overview: str
    key_contacts: list[str]
    competitive_positioning: str
    recommended_approach: str
    talking_points: list[str]
    risks_and_objections: list[str]
    budget_indicators: Optional[str] = None
    next_steps: list[str]
    confidence_score: float = Field(ge=0, le=100)
    data_sources_used: list[str] = Field(default_factory=list)
