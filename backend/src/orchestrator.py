from __future__ import annotations

import json
from typing import Any, Optional

from openai import AsyncOpenAI

from .logging_config import get_logger
from .models import (
    AggregatedIntelligence,
    AnalysisRequest,
    BattleCard,
    BattleCardDraft,
    SourceStatus,
)
from .settings import Settings
from .utils import extract_json_object, format_bullet_list


class GTMOrchestrator:
    def __init__(self, settings: Settings, client: Optional[AsyncOpenAI] = None):
        self.settings = settings
        self.client = client or AsyncOpenAI(
            api_key=settings.github_models_token,
            base_url=settings.github_models_base_url,
            timeout=settings.github_models_timeout_seconds,
        )
        self._owns_client = client is None

    async def close(self) -> None:
        if self._owns_client:
            await self.client.close()

    async def synthesize_battle_card(
        self,
        request: AnalysisRequest,
        intelligence: AggregatedIntelligence,
        source_status: dict[str, SourceStatus],
        *,
        run_id: str,
    ) -> BattleCard:
        logger = get_logger(__name__, run_id)
        prompt = self._build_prompt(request, intelligence)

        try:
            response = await self.client.chat.completions.create(
                model=self.settings.github_models_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a GTM strategist. Generate a factual, account-specific battle card. "
                            "Return strict JSON only."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self.settings.github_models_temperature,
                max_tokens=self.settings.github_models_max_tokens,
                response_format={"type": "json_object"},
            )
            model_text = response.choices[0].message.content or ""
            payload = extract_json_object(model_text)
            draft = BattleCardDraft.model_validate(payload)
            logger.info("LLM synthesis succeeded.")
        except Exception as exc:
            logger.warning("LLM synthesis failed, using deterministic fallback: %s", exc)
            draft = self._fallback_draft(request, intelligence)

        used_sources = [
            key for key, value in source_status.items() if value.status in {"success", "degraded"}
        ]
        confidence = self._compute_confidence(source_status, draft)

        return BattleCard(
            account_name=request.company_name,
            account_id=request.account_id,
            company_overview=draft.company_overview,
            key_contacts=draft.key_contacts,
            competitive_positioning=draft.competitive_positioning,
            recommended_approach=draft.recommended_approach,
            talking_points=draft.talking_points,
            risks_and_objections=draft.risks_and_objections,
            budget_indicators=draft.budget_indicators,
            next_steps=draft.next_steps,
            confidence_score=confidence,
            data_sources_used=used_sources,
        )

    async def format_battle_card_markdown(
        self,
        battle_card: BattleCard,
        *,
        run_id: str,
    ) -> str:
        logger = get_logger(__name__, run_id)
        prompt = (
            "Convert this battle card JSON into concise, readable markdown for sales reps. "
            "Use sections: Company Snapshot, Recommended Approach, Talking Points, Risks, Next Steps. "
            "Do not invent facts.\n\n"
            f"{json.dumps(battle_card.model_dump(mode='json'), indent=2)}"
        )
        try:
            response = await self.client.chat.completions.create(
                model=self.settings.github_models_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a sales enablement writer. Return markdown only.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self.settings.github_models_temperature,
                max_tokens=self.settings.github_models_max_tokens,
            )
            text = response.choices[0].message.content or ""
            if text.strip():
                return text.strip()
        except Exception as exc:
            logger.warning("Markdown formatting call failed, using local fallback: %s", exc)
        return self._fallback_markdown(battle_card)

    @staticmethod
    def _build_prompt(request: AnalysisRequest, intelligence: AggregatedIntelligence) -> str:
        tool_outputs = {
            "search_company_data": {
                "company_name": intelligence.company_intel.company_name,
                "industry": intelligence.company_intel.industry,
                "employee_count": intelligence.company_intel.employee_count,
                "funding_stage": intelligence.company_intel.funding_stage,
                "technologies": intelligence.company_intel.technologies,
                "intent_signals": intelligence.company_intel.intent_signals,
            },
            "analyze_call_patterns": [
                {
                    "topics": call.topics,
                    "sentiment": call.sentiment,
                    "objections": call.objections_raised,
                    "next_steps": call.next_steps_mentioned,
                }
                for call in intelligence.recent_calls
            ],
            "identify_buying_committee": [
                {
                    "name": contact.name,
                    "title": contact.title,
                    "seniority": contact.seniority,
                }
                for contact in intelligence.top_contacts
            ],
        }
        return (
            f"Account ID: {request.account_id}\n"
            f"Company: {request.company_name}\n"
            f"Industry hint: {request.industry or 'Unknown'}\n\n"
            "Tool outputs:\n"
            f"{json.dumps(tool_outputs, indent=2)}\n\n"
            "Return JSON only with fields:\n"
            "{\n"
            '  "company_overview": string,\n'
            '  "key_contacts": string[],\n'
            '  "competitive_positioning": string,\n'
            '  "recommended_approach": string,\n'
            '  "talking_points": string[],\n'
            '  "risks_and_objections": string[],\n'
            '  "budget_indicators": string | null,\n'
            '  "next_steps": string[]\n'
            "}\n"
            "Constraints:\n"
            "- 3-7 key_contacts\n"
            "- 3-8 talking_points\n"
            "- 2-8 risks_and_objections\n"
            "- 2-8 next_steps\n"
            "- Keep output specific to the provided account context.\n"
        )

    @staticmethod
    def _compute_confidence(
        source_status: dict[str, SourceStatus], draft: BattleCardDraft
    ) -> float:
        score = 55.0
        apollo_enrich = source_status.get("apollo_enrich")
        if apollo_enrich and apollo_enrich.status == "success":
            score += 20
        elif apollo_enrich and apollo_enrich.status == "degraded":
            score += 8

        if source_status.get("gong_mock"):
            score += 8
        if source_status.get("apollo_contacts"):
            score += 8

        if len(draft.talking_points) >= 5:
            score += 4
        if len(draft.next_steps) >= 4:
            score += 5

        return round(max(0.0, min(100.0, score)), 1)

    @staticmethod
    def _fallback_draft(
        request: AnalysisRequest, intelligence: AggregatedIntelligence
    ) -> BattleCardDraft:
        company = intelligence.company_intel
        contacts = [
            f"{contact.name} ({contact.title})" for contact in intelligence.top_contacts[:5]
        ]
        if len(contacts) < 3:
            contacts.extend(
                [
                    "VP Operations (target)",
                    "Head of Data/Analytics (target)",
                    "Procurement owner (target)",
                ]
            )
        contacts = contacts[:5]

        top_topics = []
        for call in intelligence.recent_calls:
            for topic in call.topics:
                if topic not in top_topics:
                    top_topics.append(topic)
        top_topics = top_topics[:3] or ["pipeline efficiency", "time-to-value", "integration risk"]

        return BattleCardDraft(
            company_overview=(
                f"{request.company_name} appears to be operating in {company.industry}. "
                f"Current signals suggest focus on {', '.join(top_topics)} with a need for clear ROI."
            ),
            key_contacts=contacts,
            competitive_positioning=(
                "Differentiate on fast implementation, measurable business outcomes, "
                "and tighter alignment to their active GTM motions."
            ),
            recommended_approach=(
                "Lead with quantified outcomes and implementation certainty. "
                "Anchor the conversation on one urgent initiative, then expand to multi-team value."
            ),
            talking_points=[
                f"Connect your offer to {topic} outcomes in the first meeting." for topic in top_topics
            ]
            + [
                "Use a short pilot plan with explicit success criteria.",
                "Show role-specific value for technical and commercial stakeholders.",
            ],
            risks_and_objections=[
                "They may claim existing tooling is sufficient; reframe around incremental ROI and speed.",
                "Integration concerns may stall deal progression; provide a concrete implementation path.",
            ],
            budget_indicators=company.recent_funding_round or company.funding_stage,
            next_steps=[
                "Confirm the primary business priority and success metric in discovery.",
                "Share a tailored POV with architecture and rollout timeline.",
                "Schedule a joint technical + business validation session.",
            ],
        )

    @staticmethod
    def _fallback_markdown(battle_card: BattleCard) -> str:
        return (
            f"## {battle_card.account_name} Battle Card\n\n"
            f"### Company Snapshot\n{battle_card.company_overview}\n\n"
            f"### Key Contacts\n{format_bullet_list(battle_card.key_contacts)}\n\n"
            f"### Recommended Approach\n{battle_card.recommended_approach}\n\n"
            f"### Talking Points\n{format_bullet_list(battle_card.talking_points)}\n\n"
            f"### Risks & Objections\n{format_bullet_list(battle_card.risks_and_objections)}\n\n"
            f"### Next Steps\n{format_bullet_list(battle_card.next_steps)}\n"
        )
