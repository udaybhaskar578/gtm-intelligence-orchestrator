# GTM Intelligence Orchestrator

## Project Specification & Technical Approach

---

## Executive Summary

This weekend project demonstrates a production-ready AI-powered GTM workflow orchestrator designed for Snorkel AI's interview process. The system integrates:

- **Real company enrichment data** (Clay API)
- **Call intelligence patterns** (Gong)
- **Prospect research** (Apollo)
- **Claude AI synthesis** for intelligent decision-making

This directly addresses the Snorkel GTM Engineer role: AI-enabled automations, multi-system integrations, and scalable workflow design.

---

## Problem Statement

GTM teams waste significant time researching prospects across disconnected tools:

- ✗ Searching Apollo for contacts
- ✗ Pulling company data from Clay
- ✗ Analyzing call patterns in Gong
- ✗ Manually synthesizing findings into actionable intelligence

**Solution:** Automate the synthesis layer using Claude AI

- → Reduce research time: **15+ minutes → <10 seconds**
- → Improve decision quality through AI reasoning

---

## Solution Overview

### What We're Building

A Python-based intelligent orchestrator that takes an account ID, fetches data from multiple GTM sources, and uses Claude's tool-use capabilities to synthesize a "battle card" for sales rep preparation.

### Core Workflow (5 Steps)

```
Step 1: Receive account ID from Salesforce webhook
         ↓
Step 2: Fetch data
        ├─ Clay enrichment (REAL API)
        └─ Gong calls (MOCKED)
         ↓
Step 3: Claude uses tool-use to reason across all sources
         ↓
Step 4: Generate battle card
        ├─ Talking points
        ├─ Risks & objections
        └─ Recommended approach
         ↓
Step 5: Store in Salesforce Account record
```

---

## Data Sources & Integration Strategy

### Clay (Real API Integration)

**Status:** ✅ Live API using 14-day free trial

Clay provides comprehensive company enrichment:

- Firmographics (size, industry, location)
- Technographics (software stack)
- Recent hiring/funding signals
- Intent signals
- Uses HTTP API (available on free trial)

**Why Real:** Shows you can actually integrate APIs; demonstrates API integration skills.

---

### Gong (Mocked with Realistic Payloads)

**Status:** 🔄 Mock data with production-like structure

Gong requires administrator access (not available in free tier).

- Mock realistic call data patterns
- Industry-specific conversation patterns
- Call duration, participants, sentiment, topics
- Production version swaps to real Gong API calls

**Why Mocked:** Respects time constraints (admin access required); shows architectural thinking about swappable data sources.

---

### Apollo (Mocked)

**Status:** 🔄 Mock data

Apollo requires Professional tier ($79+/mo) for API access.

- Mock contact data at company level
- Integration pattern is production-ready
- Can swap real API at deployment without changing core logic

**Why Mocked:** Time pragmatism; shows you understand the integration pattern.

---

## Claude Agent Design

### Tool-Use Architecture

Claude operates as an intelligent orchestrator with specialized capabilities:

#### 1. **Search Company Data**
- Query Clay results for specific attributes
- Extract technographics, hiring signals, funding status
- Identify relevant insights for sales approach

#### 2. **Analyze Call Patterns**
- Extract sentiment from call history
- Identify discussion topics and objections
- Recognize buying signals and pain points

#### 3. **Synthesize Intelligence**
- Correlate data across sources
- Generate strategic recommendations
- Identify competitive positioning opportunities

#### 4. **Build Battle Card**
- Produce structured output with talking points
- Document risks and potential objections
- Recommend personalized sales approach

### Reasoning Flow

```
Raw Data (Clay + Gong + Apollo)
         ↓
Claude Tool-Use Agent
├─ Tool 1: Search company attributes
├─ Tool 2: Analyze call sentiment
├─ Tool 3: Extract objection patterns
└─ Tool 4: Generate recommendations
         ↓
Structured Battle Card
```

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| **Language** | Python 3.11 |
| **Framework** | FastAPI (async HTTP server) |
| **AI/LLM** | Claude API (Sonnet 4) with tool-use |
| **HTTP Client** | httpx (async requests) |
| **Data Validation** | Pydantic v2 |
| **CRM Integration** | Salesforce REST API |
| **Config Management** | python-dotenv |
| **Dev Environment** | Cursor Pro / VS Code |

---

## Weekend Deliverables

### Code Repository

```
snorkel-gtm-agent/
├── gtm_orchestrator.py      # Core agent orchestration logic
├── data_sources.py          # Clay (real), Gong (mock), Apollo (mock)
├── models.py                # Pydantic data structures
├── salesforce_handler.py    # CRM write-back logic
├── requirements.txt         # Python dependencies
├── .env.example            # Configuration template
├── README.md               # Architecture & usage guide
└── .gitignore
```

### Demo Assets

- **Example battle card output** (JSON + formatted markdown)
- **2-minute demo video** showing:
  - Webhook trigger from Salesforce
  - Clay API data fetch
  - Claude synthesis with reasoning
  - Battle card generation
  - Salesforce record update

---

## Key Design Decisions

### Why This Approach Demonstrates Snorkel Fit

#### 1. **GTM Engineering Focus**
Directly addresses job spec—automations across Salesforce, Clay, Gong, and Claude. Shows understanding of GTM operational complexity.

#### 2. **Production Thinking**
- Error handling and retry logic
- Logging and observability
- Data validation at every layer
- Configuration management
- Type safety with Pydantic

#### 3. **Scalable Architecture**
Demonstrates a blueprint for extending to:
- Lead routing (automated assignment based on company fit)
- Deal support (context for ongoing deals)
- Forecasting (predict close probability)
- Account research (enrich account records)

#### 4. **Real vs. Mock Pragmatism**
- Clay is **real** (shows API integration chops)
- Gong/Apollo are **mocked** (respects time constraints)
- Code organized to **swap real APIs instantly** without changing logic
- Shows mature engineering judgment

#### 5. **Claude-Native Approach**
- Uses tool-use and agentic reasoning
- Not just a wrapper around API calls
- Demonstrates understanding of LLM reasoning
- Production-grade prompt engineering

---

## Interview Narrative

**What to say Monday morning:**

> "I built an intelligence orchestrator that pulls company data from Clay, call patterns from Gong, and prospect research, then uses Claude's tool-use to synthesize a battle card in seconds.
>
> The core workflow is: Salesforce webhook trigger → fetch enriched data → Claude reasons across sources → generate sales intelligence → write back to CRM.
>
> This architecture is the pattern for your GTM automation stack: pull from your sources, let Claude reason about it, push results back to Salesforce.
>
> I built Clay integration **real** on the free trial to show API chops, mocked Gong **respectfully** (admin-only access), and demonstrated error handling, logging, and production design throughout.
>
> The codebase is organized to swap real APIs for mocks instantly. You'd apply this same pattern to lead routing, deal support, and forecasting workflows."

---

## Success Metrics

- ✅ **Reduce research time:** 15+ minutes → <10 seconds
- ✅ **Multi-source synthesis:** Clay + Gong + Apollo in one structured output
- ✅ **Production readiness:** Error handling, retry logic, logging, type safety
- ✅ **Scalability pattern:** Code ready to extend to other GTM workflows
- ✅ **Real integration:** Clay API working end-to-end
- ✅ **Professional output:** Battle card with actionable intelligence

---

## Implementation Plan

### Phase 1: Setup & Core (Saturday Evening)
- [ ] Initialize repo and git
- [ ] Create Python environment and install dependencies
- [ ] Set up Pydantic models for data structures
- [ ] Create .env template

### Phase 2: Data Sources (Saturday Night)
- [ ] Implement Clay API client (real)
- [ ] Create Gong mock data generator
- [ ] Create Apollo mock data generator
- [ ] Write tests for data sources

### Phase 3: Claude Agent (Sunday Morning)
- [ ] Define Claude tool schemas
- [ ] Build orchestrator logic
- [ ] Implement tool-use agent loop
- [ ] Create battle card generation logic

### Phase 4: Integration & Demo (Sunday Afternoon)
- [ ] Build Salesforce handler
- [ ] Create example output
- [ ] Record 2-minute demo
- [ ] Polish README documentation

### Phase 5: Polish & Review (Sunday Evening)
- [ ] Code review and refactoring
- [ ] Error handling audit
- [ ] Documentation review
- [ ] Final commit and cleanup

---

## Next Steps (Long-term)

### Phase 1: This Weekend
Build orchestrator with Clay API + mocked Gong/Apollo

### Phase 2: Production Deployment
Swap mocks for real Gong/Apollo APIs (with admin/paid access)

### Phase 3: Scale & Extend
Apply same pattern to:
- Lead routing automation
- Deal support workflows
- Forecasting pipelines
- Account research engine

---

## Technical Considerations

### Error Handling Strategy
- Retry logic with exponential backoff for API calls
- Graceful degradation if any data source fails
- Comprehensive logging at each stage
- Clear error messages for debugging

### Data Privacy
- No sensitive data logging
- Secure .env handling for API keys
- Type validation prevents data type mismatches
- Audit trail of all synthesis decisions

### Performance
- Async HTTP requests with httpx
- Parallel data fetching from multiple sources
- Efficient Claude API calls with structured prompts
- Caching opportunities for repeated lookups

### Maintainability
- Clear separation of concerns (data sources, agent, CRM handler)
- Pydantic models define contracts between modules
- Comprehensive README with architecture diagrams
- Well-commented code for future extensions

---

## Questions for Hiring Manager (Demo Follow-up)

If asked about production readiness:

> "In production, I'd add:
> - Request queuing for burst traffic
> - Caching layer for repeated company lookups
> - Webhook retry mechanism for Salesforce failures
> - Analytics pipeline to track battle card accuracy
> - A/B testing framework for Claude prompt variations"

---

## Files Generated

✅ This document: `GTM_ORCHESTRATOR_PROJECT_PLAN.md`
- Complete project specification
- Technical architecture
- Implementation roadmap
- Interview talking points

📁 Repository structure ready to build:
```
snorkel-gtm-agent/
├── README.md (comprehensive)
├── .env.example
├── requirements.txt
├── gtm_orchestrator.py
├── data_sources.py
├── models.py
├── salesforce_handler.py
└── example_output.json
```

---

## Ready to Build?

This project is designed to be completed in one weekend while demonstrating:
- ✅ Real API integration skills
- ✅ AI/LLM orchestration capabilities
- ✅ Production-grade Python engineering
- ✅ GTM domain knowledge
- ✅ Architectural thinking

**Start with Phase 1 Setup, then follow the implementation plan sequentially.**

Good luck Monday! 🚀
