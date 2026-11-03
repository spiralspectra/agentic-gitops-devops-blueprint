# Multi-Agent Package on Vertex AI Agent Engine (Archetype 1)

Production-grade Google Agent Development Kit (ADK) multi-agent package deployed to **Vertex AI Agent Engine** and publishable to enterprise AI interfaces and Agent2Agent (A2A) networks.

---

## Architecture & Layout

This archetype implements a multi-agent system composed of a top-level orchestrator routing to three specialized domain pillars:

```text
agents/starter_agent/
├── app/
│   ├── agent.py                  # <100-line composition root: root_agent (gemini-2.5-flash) + 3 pillars (gemini-2.5-pro)
│   ├── core/
│   │   ├── config.py             # 12-Factor env configuration (models, BigQuery datasets, WIF, auth)
│   │   ├── bq.py                 # Fail-closed get_caller_bq_client() (OAuth + Entra ID WIF OIDC + RLS dry-run)
│   │   ├── guardrails.py         # 3-layer sensitive compensation guardrail & recursive output redaction
│   │   └── canvas.py             # Signed A2UI WebFrameUrl workbench & scorecard builder
│   ├── pillars/
│   │   ├── pillar1_operations.py # Operational Intelligence: daily shift briefings, task tracking, RLS metrics
│   │   ├── pillar2_catalog.py    # Catalog, Pricing & Knowledge Graph: semantic discovery & A2UI canvas launcher
│   │   └── pillar3_studio.py     # Campaign Studio: compliance-gated asset drafting & human confirmation
│   ├── marketing_studio.py       # Human-in-the-loop campaign asset filing and governance engine
│   ├── ontology.py               # 3-layer Knowledge Catalog Context Set, Glossary, & SQL 5 GiB dry-run guard
│   ├── ontology_data/            # Declarative context_set.json & semantic_ontology.yaml
│   ├── fast_api_app.py           # FastAPI / Agent Runtime A2A & ADK server entrypoint
│   └── app_utils/                # VertexAiSessionService, OTel GenAI telemetry, A2A & Reasoning Engine adapters
├── agents-cli-manifest.yaml      # agents-cli deployment manifest for Vertex AI Agent Engine
├── deployment_metadata.json      # Deployed engine tracking metadata
├── pyproject.toml                # Locked package dependencies and tools
└── README.md
```

---

## 3-Pillar Multi-Agent Model

| Sub-Agent | Specialist Role | Model | Primary Tools |
| :--- | :--- | :--- | :--- |
| **`operations_agent`** (Pillar 1) | Operational intelligence, daily shift summaries, team tasks | `gemini-2.5-pro` | `get_daily_operational_metrics`, `get_shift_briefing`, `open_operations_workbench` |
| **`catalog_agent`** (Pillar 2) | Product discovery, pricing models, POI & customer segment matching | `gemini-2.5-pro` | `search_catalog_items`, `calculate_dynamic_quote`, `open_item_detail_canvas`, `lookup_knowledge_catalog_context` |
| **`studio_agent`** (Pillar 3) | Campaign creation, copy drafting, compliance check, publishing | `gemini-2.5-pro` | `draft_campaign_asset`, `validate_copy_compliance`, `file_campaign_to_store` (gated `confirmed=True`) |

---

## Zero-Trust Security & Guardrails

1. **Caller Identity Propagation**: `get_caller_bq_client` extracts user credentials from context (Google OAuth or verified Entra ID OIDC JWT tokens via Workload Identity Federation) ensuring BigQuery Row-Level Security (`SESSION_USER()`) is enforced at the database level.
2. **Sensitive Data Guardrail**:
   - Prompt-layer instruction refusing requests for individual pay, salary, or executive remuneration.
   - Pre-query regex gate (`assert_no_restricted_pay_data`) rejecting unauthorized SQL statements.
   - Post-execution recursive redaction (`redact_restricted_pay_fields`) removing restricted field patterns from agent responses.
3. **BigQuery Query Budget**: Strict dry-run quota validation enforcing a 5 GiB per-query limit (`MAX_BYTES_BILLED`) before executing ad-hoc queries.

---

## Developer Quickstart

### 1. Install Dependencies & Configure Environment

```bash
cd agents/starter_agent

# Install dependencies using uv
uv sync

# Configure environment
cp .env.example .env
```

Key environment variables in `.env`:

```dotenv
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-central1
BQ_DATASET_ID=enterprise_lakehouse
AGENT_ROUTER_MODEL=gemini-2.5-flash
AGENT_PILLAR_MODEL=gemini-2.5-pro
REQUIRE_CALLER_IDENTITY=false # Set to true in production to mandate verified end-user JWT
```

### 2. Run Locally via ADK CLI

```bash
# Test single-turn execution
printf "Provide the operational morning briefing for unit 001.\nexit\n" | uv run adk run app

# Run interactive developer playground
uvx google-agents-cli@1.11.0 playground
```

### 3. Deploy to Vertex AI Agent Engine

```bash
# Validate manifest and package
agents-cli check

# Deploy to Vertex AI Agent Engine
agents-cli deploy \
  --project="your-gcp-project-id" \
  --region="us-central1"

# Publish agent to Gemini Enterprise catalog
agents-cli publish \
  --project="your-gcp-project-id" \
  --region="us-central1"
```

---

## Testing & Evaluation

| Test Type | Scope | Command |
| :--- | :--- | :--- |
| **Unit Tests** | Security guardrails, SQL sanitization, data redaction | `uv run pytest tests/unit -v` |
| **Integration Tests** | Multi-turn pillar handoffs and FastAPI/A2A endpoints | `uv run pytest tests/integration -v` |
| **Evaluation Suite** | Golden prompt datasets, hallucination checks, groundedness | `uvx google-agents-cli eval run --concurrency 4` |
