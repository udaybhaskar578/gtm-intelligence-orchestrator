from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


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
