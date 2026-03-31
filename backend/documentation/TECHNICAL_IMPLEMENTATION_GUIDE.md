# GTM Intelligence Orchestrator - Technical Implementation Guide

**For:** Cursor Pro / Codex code generation  
**Project:** Snorkel AI interview weekend project  
**Timeframe:** 48 hours (Saturday-Sunday)  
**Status:** Ready for implementation

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture & Design](#architecture--design)
3. [Technology Stack](#technology-stack)
4. [API Integration Details](#api-integration-details)
5. [Data Models & Schemas](#data-models--schemas)
6. [Core Module Specifications](#core-module-specifications)
7. [Claude Agent Design](#claude-agent-design)
8. [Error Handling & Logging](#error-handling--logging)
9. [File Structure & Scaffolding](#file-structure--scaffolding)
10. [Development Phases](#development-phases)
11. [Testing & Validation](#testing--validation)

---

## Project Overview

### What We're Building

A Python-based AI-powered GTM workflow orchestrator that:
- Takes a Salesforce account ID as input
- Fetches real company enrichment data from Clay API
- Fetches mocked call intelligence from Gong (mocked for free tier)
- Fetches mocked prospect research from Apollo (mocked for free tier)
- Uses Claude/GPT-4 via GitHub Models to synthesize intelligence
- Generates a "battle card" with talking points, risks, and sales approach
- Writes results back to Salesforce Account record

### Success Criteria

1. **Clay API Integration (Real):** Working end-to-end with 14-day free trial
2. **Gong/Apollo Mocks:** Production-like mock data with realistic patterns
3. **Claude Agent:** Tool-use orchestrator that synthesizes cross-source intelligence
4. **Battle Card Output:** Structured JSON with actionable sales intelligence
5. **Production Code Quality:** Error handling, logging, type safety throughout
6. **Demo-Ready:** Complete working example with sample output
7. **Interview Narrative:** Code clearly demonstrates GTM engineering mindset

---

## Architecture & Design

### System Diagram

```
Salesforce Account Record
         ↓ (webhook/API call)
         ↓ Account ID
┌────────────────────────────────────┐
│   GTM Intelligence Orchestrator    │
│                                    │
│  ┌─────────────────────────────┐  │
│  │  Input Validation Layer     │  │
│  │  (Pydantic models)          │  │
│  └────────────┬────────────────┘  │
│               ↓                    │
│  ┌──────────────────────────────┐ │
│  │  Data Fetching (Parallel)    │ │
│  │  ├─ Clay API (REAL)          │ │
│  │  ├─ Gong Mock                │ │
│  │  └─ Apollo Mock              │ │
│  └────────────┬─────────────────┘ │
│               ↓                    │
│  ┌──────────────────────────────┐ │
│  │  Claude Agent Orchestrator   │ │
│  │  ├─ Tool 1: Search company   │ │
│  │  ├─ Tool 2: Analyze calls    │ │
│  │  ├─ Tool 3: Extract risks    │ │
│  │  └─ Tool 4: Generate insights│ │
│  └────────────┬─────────────────┘ │
│               ↓                    │
│  ┌──────────────────────────────┐ │
│  │  Battle Card Generator       │ │
│  │  (Structured JSON output)    │ │
│  └────────────┬─────────────────┘ │
│               ↓                    │
│  ┌──────────────────────────────┐ │
│  │  Salesforce Write-back       │ │
│  │  (Account record update)     │ │
│  └──────────────────────────────┘ │
└────────────────────────────────────┘
         ↓
    Salesforce Account Record
    (updated with battle card)
```

### Key Design Patterns

1. **Layered Architecture:**
   - Input/validation layer (Pydantic)
   - Data fetching layer (async httpx)
   - Agent orchestration layer (Claude/GPT-4)
   - Output generation layer
   - CRM integration layer

2. **Separation of Concerns:**
   - `models.py` - Data structures only (Pydantic)
   - `data_sources.py` - API clients and mock data
   - `gtm_orchestrator.py` - Agent orchestration logic
   - `salesforce_handler.py` - CRM integration
   - `main.py` or `app.py` - FastAPI entry point (optional)

3. **Async-First:**
   - Use `asyncio` and `httpx` for concurrent API calls
   - Fast parallel fetching from multiple sources
   - Graceful degradation if one source fails

4. **Error Handling:**
   - Try-except with logging at each layer
   - Retry logic for flaky APIs
   - Fallback values for missing data
   - Never crash, always return partial results

---

## Technology Stack

### Core Technologies

| Component | Technology | Why |
|-----------|-----------|-----|
| **Language** | Python 3.11+ | Mature, async support, great for AI/ML |
| **Package Manager** | pip | Standard, reliable |
| **LLM API** | GitHub Models (OpenAI SDK) | Free, OpenAI-compatible, tool-calling support |
| **HTTP Client** | httpx | Async, modern, works with OpenAI SDK |
| **Data Validation** | Pydantic v2 | Type safety, automatic validation, great errors |
| **API Framework** | FastAPI (optional) | If building webhook endpoint, not required for demo |
| **Environment** | python-dotenv | Secure API key management |
| **Development** | Cursor Pro | AI-assisted coding, faster implementation |
| **Runtime** | Python venv | Isolated dependencies |

### Dependencies (requirements.txt)

```
openai==1.0.0              # OpenAI SDK (works with GitHub Models)
python-dotenv==1.0.0       # Environment variable management
httpx==0.27.0              # Async HTTP client
pydantic==2.7.1            # Data validation
pydantic-settings==2.0.0   # Pydantic settings management
aiohttp==3.9.0             # Alternative async HTTP (optional)
typing-extensions==4.8.0   # Extended type hints
python-json-logger==2.0.7  # JSON logging (optional, for production)
```

---

## API Integration Details

### 1. GitHub Models (LLM Provider) - FREE TIER

**Setup:**
1. Create GitHub Personal Access Token (PAT)
   - Settings → Developer settings → Personal access tokens → Fine-grained tokens
   - Permissions: Account permissions → Models → Read-only
   - Expiration: No expiration

2. Store token in `.env`:
   ```
   GITHUB_MODELS_TOKEN=github_pat_11AHx...
   ```

**API Details:**
- **Base URL:** `https://models.inference.ai.azure.com`
- **Endpoint:** `/chat/completions`
- **Authentication:** Bearer token in Authorization header
- **Model:** `gpt-4` (or `openai/gpt-4.1` for newer version)
- **Rate Limits (Free):**
  - Requests per minute: 10
  - Requests per day: 50
  - Tokens per request: 8000 input / 4000 output
  - Concurrent requests: 2

**Implementation:**
```python
from openai import AsyncOpenAI

client = AsyncOpenAI(
    api_key=os.getenv("GITHUB_MODELS_TOKEN"),
    base_url="https://models.inference.ai.azure.com"
)

response = await client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": prompt}],
    tools=tools,
    tool_choice="auto"
)
```

### 2. Clay API (Company Enrichment) - REAL INTEGRATION

**Setup:**
1. Sign up for Clay free trial (14 days, 1000 credits)
   - https://clay.com
2. Verify email
3. Copy API key from account settings

**API Details:**
- **Base URL:** `https://api.clay.com/v1`
- **Authentication:** API key in header `Authorization: Bearer {API_KEY}`
- **Endpoints Used:**
  - `POST /api/v1/sources` - Create enrichment source
  - `POST /api/v1/tables/rows/enrichment` - Enrich company data

**Implementation:**
```python
class ClayClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.clay.com/v1"
        self.client = httpx.AsyncClient()
    
    async def enrich_company(self, company_name: str) -> CompanyIntel:
        # Use Clay HTTP API to fetch company enrichment
        # Returns: firmographics, technographics, signals
        pass
```

**Mock Data (if trial expires):**
- Use realistic company profiles by industry
- Include: firm size, industry, funding, hiring signals, recent news, intent signals
- See `data_sources.py` ClayDataSource.enrich_company() for patterns

### 3. Gong (Call Intelligence) - MOCKED

**Reason:** Gong requires admin access (not available in free tier)

**Mock Implementation:**
```python
class GongDataSource:
    @staticmethod
    def find_calls(company_name: str, limit: int = 3) -> List[CallInsight]:
        """
        Return realistic mock call data:
        - Call ID, duration, date, participants
        - Topics discussed
        - Sentiment (positive/neutral/negative)
        - Key discussion points
        
        Pattern by industry:
        - AI/ML: data quality, pipeline, budgets
        - Finance: risk mgmt, compliance, ROI
        - Healthcare: HIPAA, integration, adoption
        """
        pass
```

**Production Swap:**
- When Gong admin access available, implement real API calls
- Same interface, swap implementation
- No changes needed to orchestrator

### 4. Apollo (Contact/Prospect Data) - MOCKED

**Reason:** Requires Professional tier ($79+/mo)

**Mock Implementation:**
```python
class ApolloDataSource:
    @staticmethod
    def search_contacts(company_name: str, limit: int = 5) -> List[Contact]:
        """
        Return realistic mock contact data:
        - Name, email, title, company
        - LinkedIn URL
        - Phone number (optional)
        
        Match contacts to company size/industry
        """
        pass
```

**Production Swap:**
- Implement when Apollo API access acquired
- Same interface, swap implementation
- No changes needed to orchestrator

### 5. Salesforce (CRM Write-back) - OPTIONAL FOR DEMO

**For this weekend demo: OPTIONAL** (mock output instead)

If implementing:
```python
class SalesforceHandler:
    def __init__(self, instance_url: str, client_id: str, client_secret: str):
        self.instance_url = instance_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.client = httpx.AsyncClient()
    
    async def update_account(self, account_id: str, battle_card: BattleCard):
        # OAuth flow, then PATCH /services/data/v57.0/sobjects/Account/{id}
        pass
```

**Alternative for demo:** Save battle card to JSON, show output

---

## Data Models & Schemas

### All Pydantic Models (models.py)

```python
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# INPUT MODELS

class AnalysisRequest(BaseModel):
    """Input request for account analysis"""
    account_id: str = Field(..., description="Salesforce Account ID")
    company_name: str = Field(..., description="Company name to analyze")
    industry: Optional[str] = Field(None, description="Optional industry")
    max_retries: int = Field(default=2)

# DATA SOURCE MODELS

class Contact(BaseModel):
    """Contact data from Apollo"""
    id: str
    name: str
    email: str
    title: str
    company: str
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    seniority: Optional[str] = None

class CompanyIntel(BaseModel):
    """Company enrichment from Clay"""
    company_name: str
    industry: str
    employee_count: int
    funding_stage: Optional[str] = None  # Seed, Series A, Series B, Public, etc.
    revenue_range: Optional[str] = None  # $5M-$10M, etc.
    technologies: List[str] = Field(default_factory=list)
    recent_news: List[str] = Field(default_factory=list)
    intent_signals: List[str] = Field(default_factory=list)
    hiring_activity: Optional[str] = None
    recent_funding_round: Optional[str] = None

class CallInsight(BaseModel):
    """Call data from Gong"""
    call_id: str
    duration_minutes: int
    date: datetime
    participants: List[str]
    topics: List[str]
    sentiment: str  # "positive", "neutral", "negative"
    key_points: List[str] = Field(default_factory=list)
    objections_raised: List[str] = Field(default_factory=list)
    next_steps_mentioned: Optional[str] = None

# INTERMEDIATE MODELS

class AggregatedIntelligence(BaseModel):
    """Combined data from all sources"""
    company_intel: CompanyIntel
    top_contacts: List[Contact]
    recent_calls: List[CallInsight]
    raw_data: dict = Field(default_factory=dict)

# OUTPUT MODELS

class BattleCard(BaseModel):
    """AI-synthesized sales intelligence"""
    account_name: str
    account_id: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Executive summary
    company_overview: str = Field(
        ..., 
        description="2-3 sentence overview of company and current state"
    )
    
    # Sales intelligence
    key_contacts: List[str] = Field(
        ...,
        description="Top 3-5 contacts to target with titles"
    )
    competitive_positioning: str = Field(
        ...,
        description="How company positions against competitors, unique angles"
    )
    
    # Engagement strategy
    recommended_approach: str = Field(
        ...,
        description="Specific messaging and approach for this account"
    )
    talking_points: List[str] = Field(
        ...,
        description="5-7 specific talking points tailored to company"
    )
    
    # Risk management
    risks_and_objections: List[str] = Field(
        ...,
        description="Anticipated objections and how to address them"
    )
    budget_indicators: Optional[str] = Field(
        None,
        description="Funding/budget signals that indicate purchasing power"
    )
    
    # Execution
    next_steps: List[str] = Field(
        ...,
        description="Specific, sequential next actions for sales rep"
    )
    
    # Quality metrics
    confidence_score: float = Field(
        ge=0, le=100,
        description="Confidence in this battle card (based on data quality)"
    )
    data_sources_used: List[str] = Field(
        default_factory=list,
        description="Which data sources contributed to this card"
    )
    
    # Raw intelligence for reference
    raw_intelligence: Optional[dict] = Field(
        None,
        description="Raw aggregated data for debugging/transparency"
    )
```

---

## Core Module Specifications

### 1. models.py

**Purpose:** Define all Pydantic data structures  
**Length:** ~300 lines  
**Key Classes:**
- `AnalysisRequest` - input validation
- `Contact`, `CompanyIntel`, `CallInsight` - data source models
- `AggregatedIntelligence` - combined data
- `BattleCard` - final output

**Validation Rules:**
- `company_name`: required, non-empty
- `employee_count`: positive integer
- `confidence_score`: 0-100 float
- `talking_points`: minimum 3 items
- `next_steps`: minimum 2 items

### 2. data_sources.py

**Purpose:** Fetch data from Clay, Gong (mock), Apollo (mock)  
**Length:** ~400 lines  
**Key Classes:**

#### ClayClient (REAL)
```python
class ClayClient:
    def __init__(self, api_key: str)
    async def enrich_company(self, company_name: str) -> CompanyIntel
    async def search_by_domain(self, domain: str) -> CompanyIntel
    async def get_intent_signals(self, company_name: str) -> List[str]
```

#### GongDataSource (MOCK)
```python
class GongDataSource:
    @staticmethod
    def find_calls(company_name: str, limit: int = 3) -> List[CallInsight]
    
    # Patterns by industry:
    # AI/ML: data quality, pipeline training, budget approval
    # Finance: risk, compliance, ROI
    # Healthcare: HIPAA, EHR integration, adoption challenges
```

#### ApolloDataSource (MOCK)
```python
class ApolloDataSource:
    @staticmethod
    def search_contacts(company_name: str, limit: int = 5) -> List[Contact]
    # Generate contacts matching company size/industry
```

#### DataSourceOrchestrator
```python
class DataSourceOrchestrator:
    async def fetch_all_sources(self, company_name: str) -> AggregatedIntelligence
    # Fetch Clay real + Gong mock + Apollo mock in parallel
    # Handle failures gracefully
    # Log which sources succeeded/failed
```

**Error Handling:**
- Clay API timeout → log, return partial data
- Mock sources never fail (by design)
- Aggregate whatever data is available
- Track data quality score

### 3. gtm_orchestrator.py

**Purpose:** Claude/GPT-4 agent that orchestrates intelligence synthesis  
**Length:** ~600 lines  
**Key Classes:**

#### ToolRegistry
```python
class ToolRegistry:
    """Define Claude tools for the agent"""
    
    @staticmethod
    def get_tools() -> List[dict]:
        return [
            {
                "name": "search_company_data",
                "description": "Search enriched company data for specific attributes",
                "input_schema": {...}
            },
            {
                "name": "analyze_call_patterns",
                "description": "Analyze call history for sentiment, topics, objections",
                "input_schema": {...}
            },
            {
                "name": "extract_sales_risks",
                "description": "Identify potential objections and risks",
                "input_schema": {...}
            },
            {
                "name": "generate_recommendations",
                "description": "Create strategic sales recommendations",
                "input_schema": {...}
            }
        ]
```

#### GTMOrchestrator (Main Agent)
```python
class GTMOrchestrator:
    def __init__(self, 
        aggregated_intel: AggregatedIntelligence,
        llm_client: AsyncOpenAI
    )
    
    async def synthesize_battle_card(self) -> BattleCard:
        """
        Main orchestration loop:
        1. Build system prompt with company context
        2. Initialize agent with tools
        3. Run agentic loop (model → tool use → loop)
        4. Extract and structure final output
        5. Return BattleCard
        """
        pass
    
    async def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        """Execute Claude-requested tool and return result"""
        if tool_name == "search_company_data":
            return self._search_company_data(tool_input)
        elif tool_name == "analyze_call_patterns":
            return self._analyze_call_patterns(tool_input)
        # etc
    
    async def _agentic_loop(self, messages: List[dict]) -> str:
        """
        Standard Claude tool-use loop:
        1. Send messages to Claude with tools
        2. Parse response for tool_use blocks
        3. Execute requested tools
        4. Add tool results back to messages
        5. Repeat until stop_reason == "end_turn"
        6. Return final text response
        """
        pass
```

#### System Prompt Template
```
You are a GTM intelligence synthesizer for enterprise sales. Your job is to analyze 
company data, call patterns, and prospect information to create a battle card that 
helps a sales rep win a deal.

You have access to:
1. Company enrichment data (Clay): firmographics, technographics, funding, hiring
2. Call insights (Gong): recent calls, sentiment, discussion topics
3. Prospect data (Apollo): key contacts, titles, experience

Use your tools to extract key insights, then synthesize a comprehensive battle card
that includes:
- Clear company overview
- Recommended sales approach
- Specific talking points for this company
- Anticipated objections and how to overcome them
- Concrete next steps

Focus on:
- Company-specific context (don't generic advice)
- Competitive differentiation angles
- Budget and buying signals
- Decision-maker mapping
- Urgency/timing indicators

Return a JSON battle card with these fields:
{
  "company_overview": "...",
  "key_contacts": [...],
  "competitive_positioning": "...",
  "recommended_approach": "...",
  "talking_points": [...],
  "risks_and_objections": [...],
  "next_steps": [...]
}
```

### 4. salesforce_handler.py

**Purpose:** Write battle card back to Salesforce (optional for demo)  
**Length:** ~200 lines  
**Key Classes:**

```python
class SalesforceHandler:
    """Handle Salesforce integration (optional for demo)"""
    
    def __init__(self, 
        instance_url: str, 
        client_id: str, 
        client_secret: str
    )
    
    async def authenticate(self) -> str:
        """OAuth2 authentication flow"""
        pass
    
    async def update_account_with_battle_card(self, 
        account_id: str, 
        battle_card: BattleCard
    ) -> bool:
        """Update Account record with battle card data"""
        # PATCH /services/data/v57.0/sobjects/Account/{id}
        # Fields to update:
        # - Description: company_overview
        # - Custom_Talking_Points__c: talking_points (JSON)
        # - Custom_Battle_Card__c: entire BattleCard (JSON)
        pass
```

**For Demo:** Skip this, save to JSON instead

### 5. main.py or app.py

**Purpose:** Entry point and orchestration  
**Length:** ~150 lines  

**Option A: Simple Script (Recommended for Demo)**
```python
async def main():
    # Load env variables
    clay_api_key = os.getenv("CLAY_API_KEY")
    github_token = os.getenv("GITHUB_MODELS_TOKEN")
    
    # Create clients
    clay = ClayClient(clay_api_key)
    llm = AsyncOpenAI(api_key=github_token, base_url="...")
    
    # Example input
    request = AnalysisRequest(
        account_id="001xx000003DHP1",
        company_name="Snorkel AI"
    )
    
    # Fetch all data
    orchestrator_data = await DataSourceOrchestrator.fetch_all_sources(
        request.company_name
    )
    
    # Synthesize battle card
    gtm_agent = GTMOrchestrator(orchestrator_data, llm)
    battle_card = await gtm_agent.synthesize_battle_card()
    
    # Output
    print(json.dumps(battle_card.model_dump(), indent=2))
    
    # Optionally save
    with open("battle_card_output.json", "w") as f:
        json.dump(battle_card.model_dump(), f, indent=2, default=str)

if __name__ == "__main__":
    asyncio.run(main())
```

**Option B: FastAPI Server (Optional)**
```python
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

app = FastAPI(title="GTM Intelligence Orchestrator")

@app.post("/analyze")
async def analyze_account(request: AnalysisRequest) -> BattleCard:
    """Analyze account and generate battle card"""
    try:
        # Implementation
        pass
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "ok"}
```

---

## Claude Agent Design

### Tool Use Architecture

Claude/GPT-4 will use tools to reason through the intelligence synthesis:

#### Tool 1: search_company_data
```json
{
  "name": "search_company_data",
  "description": "Search and filter company enrichment data",
  "input_schema": {
    "type": "object",
    "properties": {
      "query": {"type": "string", "description": "What to search for (e.g., 'funding stage', 'technologies used')"},
      "filter_by": {"type": "string", "enum": ["industry", "funding", "size", "technologies"]}
    },
    "required": ["query"]
  }
}
```

#### Tool 2: analyze_call_patterns
```json
{
  "name": "analyze_call_patterns",
  "description": "Analyze call history for trends, sentiment, topics",
  "input_schema": {
    "type": "object",
    "properties": {
      "analysis_type": {
        "type": "string",
        "enum": ["sentiment_trends", "objections", "discussion_topics", "decision_signals"],
        "description": "What aspect of calls to analyze"
      }
    },
    "required": ["analysis_type"]
  }
}
```

#### Tool 3: identify_risks
```json
{
  "name": "identify_risks",
  "description": "Extract anticipated objections and risks from data",
  "input_schema": {
    "type": "object",
    "properties": {
      "context": {"type": "string", "description": "Context for risk analysis"}
    }
  }
}
```

#### Tool 4: generate_recommendations
```json
{
  "name": "generate_recommendations",
  "description": "Generate strategic sales recommendations based on all available data",
  "input_schema": {
    "type": "object",
    "properties": {
      "focus_area": {
        "type": "string",
        "enum": ["messaging", "approach", "objection_handling", "next_steps"]
      }
    },
    "required": ["focus_area"]
  }
}
```

### Agent Loop Flow

```
1. System prompt loaded with company context
2. Send initial prompt + tools to Claude
3. Claude reads data, identifies what tools to use
4. Claude calls tools (search_company_data, analyze_calls, etc.)
5. Orchestrator executes tools and returns results
6. Claude processes results, may call more tools
7. Claude builds conclusions
8. Claude calls final tool or returns JSON BattleCard
9. Loop ends when stop_reason == "end_turn"
10. Parse final message and return BattleCard
```

### Response Parsing

Claude's final message will contain:
```json
{
  "company_overview": "Snorkel AI is a Series B data labeling platform...",
  "key_contacts": ["John Doe (VP Sales)", "Jane Smith (CTO)"],
  "competitive_positioning": "vs Labelbox: stronger in...",
  "recommended_approach": "Lead with data quality ROI...",
  "talking_points": [
    "30% faster labeling with AI assistance",
    "Enterprise-grade security and compliance",
    "...",
  ],
  "risks_and_objections": [
    "Concern: Data security → Emphasize SOC2, encryption",
    "...",
  ],
  "next_steps": [
    "1. Schedule 30-min discovery call with data team",
    "2. Share relevant case study from similar company",
    "3. ...",
  ]
}
```

---

## Error Handling & Logging

### Logging Strategy

```python
import logging
import json
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Usage in code:
logger.info(f"Starting analysis for {company_name}")
logger.error(f"Clay API failed: {e}", exc_info=True)
logger.debug(f"Aggregated intelligence: {intel}")
```

### Error Handling Patterns

#### API Calls (Clay, GitHub Models)
```python
async def call_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    max_retries: int = 3,
    backoff_factor: float = 2.0
) -> dict:
    """Retry with exponential backoff"""
    for attempt in range(max_retries):
        try:
            response = await client.request(method, url)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, httpx.TimeoutException) as e:
            if attempt < max_retries - 1:
                wait_time = backoff_factor ** attempt
                logger.warning(
                    f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {e}"
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"All {max_retries} attempts failed: {e}")
                raise
```

#### Tool Execution (Claude Agent)
```python
async def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
    try:
        logger.info(f"Executing tool: {tool_name}")
        
        if tool_name == "search_company_data":
            result = self._search_company_data(tool_input)
        else:
            result = {"error": f"Unknown tool: {tool_name}"}
        
        logger.debug(f"Tool result: {result}")
        return json.dumps(result)
    
    except Exception as e:
        logger.error(f"Tool execution failed: {e}", exc_info=True)
        return json.dumps({"error": str(e)})
```

#### Graceful Degradation
```python
async def fetch_all_sources(self, company_name: str) -> AggregatedIntelligence:
    results = {}
    errors = []
    
    # Clay (real) - critical
    try:
        results['company_intel'] = await self.clay.enrich_company(company_name)
    except Exception as e:
        logger.error(f"Clay enrichment failed: {e}")
        errors.append(("Clay", str(e)))
        results['company_intel'] = CompanyIntel.default()  # Fallback
    
    # Gong (mock) - never fails
    results['calls'] = self.gong.find_calls(company_name)
    
    # Apollo (mock) - never fails
    results['contacts'] = self.apollo.search_contacts(company_name)
    
    if errors:
        logger.warning(f"Some sources failed: {errors}")
    
    return AggregatedIntelligence(**results)
```

---

## File Structure & Scaffolding

### Complete Directory Layout

```
snorkel-gtm-agent/
├── .env.example                    # Template for env variables
├── .env                            # Actual env vars (git ignored)
├── .gitignore                      # Exclude .env, __pycache__, etc.
├── requirements.txt                # Dependencies
├── README.md                        # User-facing documentation
├── ARCHITECTURE.md                 # Architecture overview (optional)
│
├── src/                            # Source code
│   ├── __init__.py
│   ├── models.py                   # Pydantic data models (~300 lines)
│   ├── data_sources.py             # Clay/Gong/Apollo clients (~400 lines)
│   ├── gtm_orchestrator.py         # Claude agent orchestrator (~600 lines)
│   ├── salesforce_handler.py       # Salesforce integration (~200 lines)
│   ├── logging_config.py           # Logging setup (optional)
│   └── utils.py                    # Helper functions (optional)
│
├── main.py                         # Entry point / demo script (~150 lines)
│
├── examples/
│   ├── example_analysis_request.json    # Sample input
│   └── example_battle_card_output.json  # Sample output
│
├── tests/                          # Unit tests (optional for demo)
│   ├── test_models.py
│   ├── test_data_sources.py
│   └── test_orchestrator.py
│
└── output/
    └── battle_card_results/        # Generated battle cards saved here
```

### .env.example Template

```bash
# GitHub Models (LLM Provider)
GITHUB_MODELS_TOKEN=github_pat_11AHx...
GITHUB_MODELS_BASE_URL=https://models.inference.ai.azure.com
GITHUB_MODELS_MODEL=gpt-4
GITHUB_MODELS_MAX_TOKENS=2000

# Clay API (Company Enrichment)
CLAY_API_KEY=your_clay_api_key_here

# Salesforce (Optional)
SALESFORCE_INSTANCE_URL=https://your-instance.salesforce.com
SALESFORCE_CLIENT_ID=your_client_id
SALESFORCE_CLIENT_SECRET=your_client_secret

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/gtm_orchestrator.log

# Feature Flags
USE_CLAY_REAL_API=true
USE_SALESFORCE_WRITE_BACK=false
SAVE_OUTPUT_TO_FILE=true
OUTPUT_DIR=output/battle_card_results
```

### Example Input (example_analysis_request.json)

```json
{
  "account_id": "001xx000003DHP1",
  "company_name": "Snorkel AI",
  "industry": "AI/Machine Learning"
}
```

### Example Output (example_battle_card_output.json)

```json
{
  "account_name": "Snorkel AI",
  "account_id": "001xx000003DHP1",
  "generated_at": "2025-03-29T17:45:23.123456",
  "company_overview": "Snorkel AI is a Series B data labeling and training platform founded in 2019 at Stanford. With ~150 employees and $35M in Series B funding, they focus on enterprise data governance and AI/ML training. Recent hiring in ML ops and GTM suggests product expansion.",
  "key_contacts": [
    "Alex Ratner (Founder & CEO)",
    "Paroma Varma (VP Engineering)",
    "Ben Mathieu (VP Sales & Strategy)"
  ],
  "competitive_positioning": "vs Labelbox: Stronger in programmatic data labeling and weak supervision. vs Scale AI: More enterprise-focused governance. Unique angle: AI-assisted labeling reduces manual effort by 30-40%.",
  "recommended_approach": "Lead with data quality ROI. Your recent Series B funding (confirmed) means budget is available. Frame as risk mitigation: reduce bad training data before it reaches models. Target data ops team first, then escalate to ML leadership.",
  "talking_points": [
    "30-40% faster labeling with AI assistance (proven in similar companies)",
    "Enterprise-grade compliance: SOC2, HIPAA-ready, data residency controls",
    "Recent hiring in ML ops indicates readiness for new tooling",
    "Series B funding cycle means budget available Q2-Q4",
    "Competitive advantage: weak supervision approach vs just manual labeling"
  ],
  "risks_and_objections": [
    {
      "objection": "We already have Labelbox",
      "approach": "Position as complementary (Snorkel enhances labeling efficiency), not replacement. Show 30% speed gain with your tool."
    },
    {
      "objection": "Data security concerns",
      "approach": "Emphasize SOC2 certification, data residency options, no training on customer data"
    },
    {
      "objection": "Integration complexity",
      "approach": "Highlight API-first design, 2-week implementation baseline"
    }
  ],
  "budget_indicators": "Series B funding ($35M) closed Q4 2024. Typical allocation: 20-30% to ops improvements. Current headcount growth in ML ops suggests $500K-$2M available for tools.",
  "next_steps": [
    "1. Connect with Ben Mathieu (VP Sales) via mutual contact - mention data labeling ROI angle",
    "2. Prepare 1-pager: 'Accelerate Training Data Quality' focused on speed gains",
    "3. Schedule 30-min discovery: ask about current labeling bottlenecks",
    "4. Share relevant case study (similar Series B ML company)",
    "5. Propose 2-week POC with their existing dataset to prove 30% speed improvement"
  ],
  "confidence_score": 87,
  "data_sources_used": ["Clay", "Gong", "Apollo"],
  "raw_intelligence": {
    "company_intel": {
      "funding_stage": "Series B",
      "recent_funding_round": "$35M Series B, Q4 2024",
      "employee_count": 150,
      "recent_hiring": ["ML Engineers", "ML Ops", "Sales Engineers"],
      "technologies": ["PyTorch", "Spark", "Python", "Kubernetes"],
      "recent_news": ["Series B announcement", "New product features", "EMEA expansion"]
    },
    "call_insights": {
      "avg_call_duration": 45,
      "sentiment_trend": "positive",
      "top_topics": ["data quality", "labeling speed", "governance"],
      "objections": ["existing tooling", "integration effort"]
    }
  }
}
```

---

## Development Phases

### Phase 1: Setup & Core Infrastructure (Saturday 2-4 hours)

**Deliverables:**
- [ ] Project repo initialized with git
- [ ] Virtual environment created
- [ ] requirements.txt with all dependencies
- [ ] .env.example template created
- [ ] GitHub Personal Access Token created and tested

**Files to Create:**
- `requirements.txt`
- `.env.example`
- `.gitignore`
- `README.md` (basic)

**Testing:**
- [ ] `pip install -r requirements.txt` works
- [ ] Environment variables load from .env
- [ ] Can import all packages

### Phase 2: Data Models (Saturday 4-6 hours)

**Deliverables:**
- [ ] All Pydantic models defined
- [ ] Input validation working
- [ ] Model serialization to JSON working

**Files to Create:**
- `src/models.py` (~300 lines)

**Testing:**
- [ ] Create sample instances of each model
- [ ] Validate JSON serialization
- [ ] Test invalid inputs (should raise validation errors)

### Phase 3: Data Sources (Saturday 6-10 hours)

**Deliverables:**
- [ ] Clay API integration working (real)
- [ ] Gong mock data generation (production-like)
- [ ] Apollo mock data generation (production-like)
- [ ] DataSourceOrchestrator fetching in parallel

**Files to Create:**
- `src/data_sources.py` (~400 lines)

**Testing:**
- [ ] Clay API enrichment returns valid CompanyIntel
- [ ] Gong mock returns realistic call patterns
- [ ] Apollo mock returns realistic contacts
- [ ] Parallel fetch completes in <2 seconds
- [ ] Error handling works (simulate Clay failure)

### Phase 4: Claude Agent (Sunday 6-8 hours)

**Deliverables:**
- [ ] Tool definitions complete
- [ ] System prompt crafted
- [ ] Agentic loop working
- [ ] Claude generates valid BattleCard JSON

**Files to Create:**
- `src/gtm_orchestrator.py` (~600 lines)

**Testing:**
- [ ] Claude calls tools appropriately
- [ ] Tool execution returns valid results
- [ ] Final JSON parses to BattleCard model
- [ ] Battle card contains all required fields
- [ ] Confidence score generated

### Phase 5: Integration & Demo (Sunday 8-10 hours)

**Deliverables:**
- [ ] Main.py entry point working
- [ ] Complete end-to-end example
- [ ] Sample output saved to JSON
- [ ] README complete with usage instructions

**Files to Create:**
- `main.py` (~150 lines)
- `examples/example_battle_card_output.json`
- Complete `README.md`

**Testing:**
- [ ] `python main.py` runs end-to-end
- [ ] Battle card output JSON matches schema
- [ ] Error handling tested (Clay timeout, etc.)

### Phase 6: Polish & Documentation (Sunday 10-11 hours)

**Deliverables:**
- [ ] Code reviewed and refactored
- [ ] All docstrings complete
- [ ] Type hints throughout
- [ ] Final commit and cleanup

**Files to Update:**
- All files: add docstrings, cleanup

---

## Testing & Validation

### Unit Tests (Optional for Demo, Recommended for Production)

```python
# tests/test_models.py
def test_company_intel_validation():
    """Test CompanyIntel validation"""
    intel = CompanyIntel(
        company_name="Test Corp",
        industry="Tech",
        employee_count=100,
        technologies=["Python", "Rust"]
    )
    assert intel.company_name == "Test Corp"
    assert len(intel.technologies) == 2

def test_battle_card_confidence_bounds():
    """Test confidence score is 0-100"""
    card = BattleCard(
        account_name="Test",
        account_id="123",
        company_overview="...",
        # ... other required fields
        confidence_score=95
    )
    assert 0 <= card.confidence_score <= 100
```

```python
# tests/test_data_sources.py
@pytest.mark.asyncio
async def test_clay_enrich_company():
    """Test Clay company enrichment"""
    clay = ClayClient(api_key="test_key")
    intel = await clay.enrich_company("Snorkel AI")
    
    assert intel.company_name == "Snorkel AI"
    assert intel.employee_count > 0
    assert len(intel.technologies) > 0

def test_gong_mock_returns_calls():
    """Test Gong mock data"""
    calls = GongDataSource.find_calls("Snorkel AI", limit=3)
    
    assert len(calls) <= 3
    assert all(isinstance(c, CallInsight) for c in calls)
    assert all(c.sentiment in ["positive", "neutral", "negative"] for c in calls)
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_end_to_end_analysis():
    """Test complete pipeline"""
    request = AnalysisRequest(
        account_id="001xx000003DHP1",
        company_name="Snorkel AI"
    )
    
    # Fetch data
    intel = await DataSourceOrchestrator.fetch_all_sources(request.company_name)
    assert intel.company_intel.company_name == "Snorkel AI"
    
    # Generate battle card
    llm = AsyncOpenAI(api_key="test_key", base_url="...")
    orchestrator = GTMOrchestrator(intel, llm)
    battle_card = await orchestrator.synthesize_battle_card()
    
    # Validate output
    assert battle_card.account_name == "Snorkel AI"
    assert len(battle_card.talking_points) >= 3
    assert len(battle_card.next_steps) >= 2
    assert 0 <= battle_card.confidence_score <= 100
```

### Manual Testing Checklist

- [ ] Run `python main.py` with Snorkel AI as test company
- [ ] Verify Clay API returns real data
- [ ] Verify Gong mock returns realistic calls
- [ ] Verify Apollo mock returns realistic contacts
- [ ] Claude generates valid BattleCard JSON
- [ ] All fields populated with non-empty values
- [ ] Talking points are company-specific (not generic)
- [ ] Recommended approach is actionable
- [ ] Next steps are sequential and specific
- [ ] JSON output can be saved to file
- [ ] Error handling works (simulate Clay failure)

---

## Key Implementation Notes

### 1. Async/Await Throughout

- Use `async def` for all I/O operations (API calls, file I/O)
- Use `asyncio.gather()` for parallel fetches
- Example:
  ```python
  clay_task = asyncio.create_task(clay.enrich_company(name))
  gong_task = asyncio.create_task(gong.find_calls(name))
  apollo_task = asyncio.create_task(apollo.search_contacts(name))
  
  company, calls, contacts = await asyncio.gather(
      clay_task, gong_task, apollo_task
  )
  ```

### 2. Claude Tool Use Loop Pattern

```python
async def _agentic_loop(self, messages: List[dict]) -> str:
    """Standard Claude tool-use loop"""
    while True:
        response = await self.llm.chat.completions.create(
            model=self.model_name,
            messages=messages,
            tools=self.tools,
            tool_choice="auto"
        )
        
        # Check stop reason
        if response.stop_reason == "end_turn":
            return response.choices[0].message.content
        
        # Handle tool use
        if response.stop_reason == "tool_use":
            tool_uses = [b for b in response.choices[0].message.content 
                        if isinstance(b, ToolUseBlock)]
            
            messages.append({
                "role": "assistant",
                "content": response.choices[0].message.content
            })
            
            for tool_use in tool_uses:
                result = await self._execute_tool(
                    tool_use.name,
                    tool_use.input
                )
                messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": result
                    }]
                })
```

### 3. Configuration Management

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    github_models_token: str
    github_models_base_url: str = "https://models.inference.ai.azure.com"
    github_models_model: str = "gpt-4"
    clay_api_key: str
    log_level: str = "INFO"
    save_output_to_file: bool = True
    output_dir: str = "output/battle_card_results"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

settings = Settings()
```

### 4. Type Safety Throughout

```python
# Always use type hints
async def enrich_company(self, company_name: str) -> CompanyIntel:
    """Enrich company data from Clay API"""
    pass

# Validate with Pydantic
def process_request(request: AnalysisRequest) -> BattleCard:
    """Process analysis request and return battle card"""
    pass
```

### 5. Production Code Quality

- Docstrings on all functions and classes
- Type hints on all parameters and returns
- Logging at INFO level for key operations
- Logging at ERROR level for failures
- Try-except blocks around external API calls
- Graceful degradation when data sources fail
- JSON serialization for all outputs
- No hardcoded values (use .env)

---

## Success Criteria for Interview

On Monday morning, you should be able to:

1. **Demo the Code:**
   - Run `python main.py` with a real company name
   - Show Clay API returning real enrichment data
   - Show Claude generating intelligent battle card
   - Show JSON output with all fields populated

2. **Explain the Architecture:**
   - Walk through data flow: Salesforce → Clay/Gong/Apollo → Claude → BattleCard
   - Explain why Clay is real (API chops) and Gong/Apollo are mocked (time/access)
   - Show tool-use agent loop and how Claude reasons through data

3. **Discuss Production Readiness:**
   - Error handling and retry logic
   - Logging and observability
   - Type safety with Pydantic
   - Async/parallel data fetching
   - Graceful degradation when sources fail

4. **Connect to GTM Engineering Role:**
   - This is the pattern for automating any GTM workflow
   - Apply same architecture to lead routing, deal support, forecasting
   - Demonstrates understanding of multi-system integration
   - Shows production engineering mindset (not just AI wrapper)

---

## Cursor Pro / Codex Prompting Guide

When using Cursor Pro to generate code, use prompts like:

### Generate Data Models
> "Create Pydantic models for GTM intelligence. Models needed: AnalysisRequest, Contact, CompanyIntel, CallInsight, AggregatedIntelligence, BattleCard. Include validation, field descriptions, and example values. See the Data Models section above for field specifications."

### Generate Data Sources
> "Implement ClayClient class with async enrich_company() method using httpx. Implement GongDataSource with mock data generation by industry. Implement ApolloDataSource with mock contacts. Include error handling, logging, and realistic mock data patterns."

### Generate Claude Agent
> "Create GTMOrchestrator class that uses Claude via OpenAI SDK (GitHub Models). Implement tool definitions for search_company_data, analyze_call_patterns, identify_risks, generate_recommendations. Implement agentic loop that calls Claude with tools until end_turn. Parse final output to BattleCard."

### Generate Main Script
> "Create main.py that demonstrates end-to-end analysis. Accept company name as input. Fetch data from Clay, Gong mock, Apollo mock in parallel. Pass to GTMOrchestrator. Generate battle card. Save output to JSON. Include example usage and error handling."

---

## Additional Resources

- GitHub Models Docs: https://docs.github.com/en/github-models
- OpenAI SDK: https://github.com/openai/openai-python
- Pydantic v2: https://docs.pydantic.dev/latest/
- Claude API Tool Use: https://docs.anthropic.com/en/docs/build-with-claude/tool-use
- Async Python: https://docs.python.org/3/library/asyncio.html

---

## Ready to Build

This document specifies everything needed to generate production-grade code with Cursor Pro/Codex.

**Next steps:**
1. Create project directory and initialize git
2. Set up Python virtual environment
3. Use Cursor Pro with the module specifications above to generate each file
4. Test each phase before moving to next
5. Polish and prepare demo for Monday

**Estimated time:** 12-16 hours of focused work across Saturday-Sunday

**Interview confidence level when done:** 95% - You'll have working code that demonstrates GTM engineering excellence
