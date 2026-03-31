from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "GTM Intelligence Orchestrator"
    log_level: str = "INFO"
    persist_output: bool = True
    output_dir: Path = Path("output/battle_card_results")
    startup_provider_check: bool = False

    github_models_token: Optional[str] = Field(default=None, alias="GITHUB_MODELS_TOKEN")
    github_models_base_url: str = Field(
        default="https://models.github.ai/inference", alias="GITHUB_MODELS_BASE_URL"
    )
    github_models_model: str = Field(default="openai/gpt-4.1", alias="GITHUB_MODELS_MODEL")
    github_models_timeout_seconds: float = Field(default=45.0, alias="GITHUB_MODELS_TIMEOUT_SECONDS")
    github_models_temperature: float = Field(default=0.2, alias="GITHUB_MODELS_TEMPERATURE")
    github_models_max_tokens: int = Field(default=1400, alias="GITHUB_MODELS_MAX_TOKENS")

    use_apollo_real_api: bool = Field(default=True, alias="USE_APOLLO_REAL_API")
    apollo_api_key: Optional[str] = Field(default=None, alias="APOLLO_API_KEY")
    apollo_enrich_base_url: str = Field(
        default="https://api.apollo.io/api/v1", alias="APOLLO_ENRICH_BASE_URL"
    )
    apollo_timeout_seconds: float = Field(default=20.0, alias="APOLLO_TIMEOUT_SECONDS")
    apollo_max_retries: int = Field(default=2, alias="APOLLO_MAX_RETRIES")

    mock_mode: str = Field(default="deterministic", alias="MOCK_MODE")
    mock_seed: int = Field(default=42, alias="MOCK_SEED")

    use_salesforce_write_back: bool = Field(default=True, alias="USE_SALESFORCE_WRITE_BACK")
    salesforce_auth_base_url: str = Field(
        default="https://login.salesforce.com",
        validation_alias=AliasChoices("SALESFORCE_AUTH_BASE_URL"),
    )
    salesforce_api_version: str = Field(default="v61.0", alias="SALESFORCE_API_VERSION")
    salesforce_client_id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("SF_CONSUMER_KEY", "SALESFORCE_CLIENT_ID"),
    )
    salesforce_client_secret: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("SF_CONSUMER_SECRET", "SALESFORCE_CLIENT_SECRET"),
    )
    salesforce_username: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("SF_USERNAME", "SALESFORCE_USERNAME"),
    )
    salesforce_password: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("SF_PASSWORD", "SALESFORCE_PASSWORD"),
    )
    salesforce_security_token: str = Field(
        default="",
        validation_alias=AliasChoices("SF_SECURITY_TOKEN", "SALESFORCE_SECURITY_TOKEN"),
    )
    sf_domain: Optional[str] = Field(default=None, validation_alias=AliasChoices("SF_DOMAIN"))
    salesforce_battle_card_field: str = Field(
        default="Battle_Card_JSON__c", alias="SALESFORCE_BATTLE_CARD_FIELD"
    )
    salesforce_summary_field: str = Field(default="Description", alias="SALESFORCE_SUMMARY_FIELD")

    @model_validator(mode="after")
    def validate_required_fields(self) -> "Settings":
        if self.sf_domain:
            domain = self.sf_domain.strip().lower()
            if domain == "login":
                self.salesforce_auth_base_url = "https://login.salesforce.com"
            elif domain == "test":
                self.salesforce_auth_base_url = "https://test.salesforce.com"
            elif domain.startswith("http://") or domain.startswith("https://"):
                self.salesforce_auth_base_url = domain.rstrip("/")
            else:
                self.salesforce_auth_base_url = f"https://{domain}.salesforce.com"

        if not self.github_models_token:
            raise ValueError("GITHUB_MODELS_TOKEN is required.")

        if self.use_apollo_real_api and not self.apollo_api_key:
            raise ValueError("APOLLO_API_KEY is required when USE_APOLLO_REAL_API=true.")

        if self.use_salesforce_write_back:
            missing = []
            if not self.salesforce_client_id:
                missing.append("SALESFORCE_CLIENT_ID")
            if not self.salesforce_client_secret:
                missing.append("SALESFORCE_CLIENT_SECRET")
            if not self.salesforce_username:
                missing.append("SALESFORCE_USERNAME")
            if not self.salesforce_password:
                missing.append("SALESFORCE_PASSWORD")
            if missing:
                raise ValueError(
                    "Missing Salesforce config when USE_SALESFORCE_WRITE_BACK=true: "
                    + ", ".join(missing)
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
