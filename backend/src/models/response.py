from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from .intelligence import Contact
from .battle_card import BattleCard


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
