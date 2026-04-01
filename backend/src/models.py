from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: str = Field(..., min_length=5, description="Salesforce Account ID")
    company_name: str = Field(..., min_length=2, description="Company to analyze")
    industry: Optional[str] = Field(default=None)
    domain: Optional[str] = Field(default=None, description="Company website domain")
    write_to_salesforce: bool = Field(default=True)
    include_raw_intelligence: bool = Field(default=False)


class Contact(BaseModel):
    id: str
    name: str
    email: str
    title: str
    company: str
    linkedin_url: Optional[str] = None
    phone: Optional[str] = None
    seniority: Optional[str] = None


class CompanyIntel(BaseModel):
    company_name: str
    industry: str
    employee_count: int = Field(default=0, ge=0)
    primary_domain: Optional[str] = None
    funding_stage: Optional[str] = None
    revenue_range: Optional[str] = None
    technologies: list[str] = Field(default_factory=list)
    recent_news: list[str] = Field(default_factory=list)
    intent_signals: list[str] = Field(default_factory=list)
    hiring_activity: Optional[str] = None
    recent_funding_round: Optional[str] = None


class CallInsight(BaseModel):
    call_id: str
    duration_minutes: int = Field(ge=1)
    date: datetime
    participants: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    sentiment: Literal["positive", "neutral", "negative"]
    key_points: list[str] = Field(default_factory=list)
    objections_raised: list[str] = Field(default_factory=list)
    next_steps_mentioned: Optional[str] = None


class AggregatedIntelligence(BaseModel):
    company_intel: CompanyIntel
    top_contacts: list[Contact] = Field(default_factory=list)
    recent_calls: list[CallInsight] = Field(default_factory=list)
    raw_data: dict[str, Any] = Field(default_factory=dict)


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


class SourceStatus(BaseModel):
    provider: str
    status: Literal["success", "degraded", "failed"]
    used_mock: bool = False
    latency_ms: int = Field(ge=0)
    error: Optional[str] = None


class SalesforceWritebackStatus(BaseModel):
    attempted: bool = False
    success: bool = False
    account_id: Optional[str] = None
    status_code: Optional[int] = None
    error: Optional[str] = None


class AnalyzeAccountResponse(BaseModel):
    run_id: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    battle_card: BattleCard
    source_status: dict[str, SourceStatus]
    salesforce_writeback: SalesforceWritebackStatus
    raw_intelligence: Optional[dict[str, Any]] = None
    top_contacts: list[Contact] = Field(default_factory=list)
