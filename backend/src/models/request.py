from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: str = Field(..., min_length=5, description="Salesforce Account ID")
    company_name: str = Field(..., min_length=2, description="Company to analyze")
    industry: Optional[str] = Field(default=None)
    domain: Optional[str] = Field(default=None, description="Company website domain")
    write_to_salesforce: bool = Field(default=True)
    include_raw_intelligence: bool = Field(default=False)
