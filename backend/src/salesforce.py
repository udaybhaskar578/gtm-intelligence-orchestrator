from __future__ import annotations

import json
from typing import Any, Optional
from urllib.parse import quote_plus

import httpx

from .logging_config import get_logger
from .models import BattleCard, SalesforceWritebackStatus
from .settings import Settings
from .utils import format_bullet_list, retry_http_request


class SalesforceClient:
    def __init__(self, settings: Settings, client: Optional[httpx.AsyncClient] = None):
        self.settings = settings
        self.client = client or httpx.AsyncClient(timeout=30.0)
        self._owns_client = client is None
        self._access_token: Optional[str] = None
        self._instance_url: Optional[str] = None

    async def close(self) -> None:
        if self._owns_client:
            await self.client.aclose()

    async def _authed_request(
        self, method: str, endpoint: str, *, run_id: str, **kwargs: Any
    ) -> httpx.Response:
        """Issue an authenticated request, retrying once on 401 after re-auth."""
        headers = {**kwargs.pop("headers", {}), "Authorization": f"Bearer {self._access_token}"}
        response = await self.client.request(method, endpoint, headers=headers, **kwargs)
        if response.status_code == 401:
            get_logger(__name__, run_id).warning("Salesforce token expired. Re-authenticating once.")
            await self._authenticate(run_id=run_id, force=True)
            headers["Authorization"] = f"Bearer {self._access_token}"
            response = await self.client.request(method, endpoint, headers=headers, **kwargs)
        return response

    async def update_account_with_battle_card(
        self,
        *,
        account_id: str,
        battle_card: BattleCard,
        run_id: str,
    ) -> SalesforceWritebackStatus:
        logger = get_logger(__name__, run_id)

        if not self.settings.use_salesforce_write_back:
            return SalesforceWritebackStatus(
                attempted=False,
                success=False,
                account_id=account_id,
                error="Salesforce write-back disabled via USE_SALESFORCE_WRITE_BACK=false",
            )

        try:
            await self._authenticate(run_id=run_id)
            payload = {
                self.settings.salesforce_battle_card_field: json.dumps(
                    battle_card.model_dump(mode="json"), default=str
                ),
                "GTM_Company_Overview__c": battle_card.company_overview,
                "GTM_Competitive_Positioning__c": battle_card.competitive_positioning,
                "GTM_Recommended_Approach__c": battle_card.recommended_approach,
                "GTM_Talking_Points__c": format_bullet_list(battle_card.talking_points, bullet="• "),
                "GTM_Risks_Objections__c": format_bullet_list(battle_card.risks_and_objections, bullet="• "),
                "GTM_Next_Steps__c": format_bullet_list(battle_card.next_steps, bullet="• "),
                "GTM_Confidence_Score__c": battle_card.confidence_score,
                "GTM_Last_Enriched__c": battle_card.generated_at.isoformat(),
                "GTM_Run_ID__c": run_id,
            }
            if self.settings.salesforce_summary_field:
                payload[self.settings.salesforce_summary_field] = battle_card.company_overview

            endpoint = (
                f"{self._instance_url}/services/data/{self.settings.salesforce_api_version}"
                f"/sobjects/Account/{account_id}"
            )
            response = await self._authed_request("PATCH", endpoint, run_id=run_id, json=payload)

            if response.status_code >= 400:
                return SalesforceWritebackStatus(
                    attempted=True,
                    success=False,
                    account_id=account_id,
                    status_code=response.status_code,
                    error=response.text[:500],
                )

            return SalesforceWritebackStatus(
                attempted=True,
                success=True,
                account_id=account_id,
                status_code=response.status_code,
            )
        except Exception as exc:
            logger.error("Salesforce write-back failed: %s", exc)
            return SalesforceWritebackStatus(
                attempted=True,
                success=False,
                account_id=account_id,
                error=str(exc),
            )

    async def list_accounts(self, *, run_id: str, limit: int = 50) -> list[dict[str, Any]]:
        await self._authenticate(run_id=run_id)
        safe_limit = max(1, min(limit, 200))
        soql = (
            "SELECT Id, Name, Industry, Website, LastModifiedDate "
            f"FROM Account ORDER BY LastModifiedDate DESC LIMIT {safe_limit}"
        )
        encoded = quote_plus(soql)
        endpoint = (
            f"{self._instance_url}/services/data/{self.settings.salesforce_api_version}"
            f"/query?q={encoded}"
        )
        response = await self._authed_request("GET", endpoint, run_id=run_id)
        response.raise_for_status()
        payload = response.json()
        return payload.get("records", [])

    async def _authenticate(self, *, run_id: str, force: bool = False) -> None:
        if self._access_token and self._instance_url and not force:
            return

        logger = get_logger(__name__, run_id)
        token_url = f"{self.settings.salesforce_auth_base_url.rstrip('/')}/services/oauth2/token"
        combined_password = (
            f"{self.settings.salesforce_password}{self.settings.salesforce_security_token or ''}"
        )
        payload = {
            "grant_type": "password",
            "client_id": self.settings.salesforce_client_id,
            "client_secret": self.settings.salesforce_client_secret,
            "username": self.settings.salesforce_username,
            "password": combined_password,
        }

        response = await retry_http_request(
            self.client,
            "POST",
            token_url,
            data=payload,
            retries=1,
        )
        parsed = response.json()
        token = parsed.get("access_token")
        instance_url = parsed.get("instance_url")
        if not token or not instance_url:
            raise RuntimeError(
                f"Salesforce auth succeeded but token payload was incomplete: {parsed}"
            )
        self._access_token = token
        self._instance_url = instance_url
        logger.info("Salesforce authentication successful.")
