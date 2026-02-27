# System Design: Enterprise AI Assistant with MCP + Guardrails

## Overview

This system provides a natural language interface to an e-commerce database, allowing business users to ask questions in plain English and receive data-driven answers with visualizations and reports.

## Architecture

```
┌─────────────────┐     ┌──────────────────────────────────────────────┐
│  Streamlit UI   │────▶│            FastAPI Backend                    │
│  (port 7860)    │     │                                              │
└─────────────────┘     │  ┌────────────┐  ┌────────────────────────┐  │
                        │  │   Input    │  │    LangGraph Agent     │  │
                        │  │ Guardrails │─▶│ Router → Agent → Tools │  │
                        │  └────────────┘  └───────────┬────────────┘  │
                        │                              │               │
                        │                   ┌──────────▼──────────┐    │
                        │                   │    MCP Server       │    │
                        │                   │    (FastMCP)        │    │
                        │                   │  ┌───────────────┐  │    │
                        │                   │  │ query_database│  │    │
                        │                   │  │ generate_chart│  │    │
                        │                   │  │ generate_report│ │    │
                        │                   │  └───────┬───────┘  │    │
                        │                   └──────────┼──────────┘    │
                        │                              │               │
                        │                   ┌──────────▼──────────┐    │
                        │                   │  Output Guardrails  │    │
                        │                   │  + Data Masking     │    │
                        │                   └──────────┬──────────┘    │
                        │                              │               │
                        │                   ┌──────────▼──────────┐    │
                        │                   │   Cost Tracker      │    │
                        │                   └──────────┬──────────┘    │
                        └──────────────────────────────┼───────────────┘
                                                       │
                                            ┌──────────▼──────────┐
                                            │    SQLite Database   │
                                            │  (e-commerce data)   │
                                            └─────────────────────┘
```

## Design Decisions

### Guardrail-First Workflow

The workflow is structured to execute Input Guardrails as the very first node after `START`. This ensures that every query—whether categorized as a data query or a general message—is validated against injection and PII patterns before any LLM processing or tool execution occurs.

### Shared Service State

The application utilizes a shared `GuardrailService` instance between the FastAPI application and the LangGraph workflow. This ensures that statistics reported via the `/guardrails/stats` endpoint accurately reflect all checks performed across the entire query lifecycle, providing a unified dashboard for the user.

### Why MCP (Model Context Protocol)?

MCP is the emerging standard for connecting AI models to external tools and data sources. By implementing our tools as MCP-compliant servers, we get:
- Standardized tool definitions with JSON Schema
- Portable tools that work with any MCP-compatible client
- Resource endpoints for schema and sample data context
- Alignment with the 2026 industry direction

### Why custom guardrails instead of NeMo/Guardrails SDK?

Custom implementation demonstrates deeper understanding of:
- Prompt injection patterns and detection strategies
- PII recognition via regex patterns
- SQL validation at the AST level (not just string matching)
- Data masking for compliance

### Why LangGraph over simple chains?

LangGraph provides:
- Cyclic workflows (agent can iterate if first attempt fails)
- Conditional routing based on intent classification
- State management across tool calls
- Critic node for output quality verification

### Why SQLite for the demo?

- Zero infrastructure (no PostgreSQL setup needed)
- Ships with Python (works in any environment)
- Deploys on HuggingFace Spaces without external DB
- Sufficient for demonstrating NL-to-SQL capabilities

## Data Flow

### Query Processing Pipeline

1. **User Input** → Streamlit sends POST to `/query`
2. **Input Guardrails** → Check for injection, PII, off-topic
3. **Router** → Classify intent (sql_query, visualization, report, general)
4. **Agent** → Select appropriate MCP tools based on intent
5. **Tool Execution** → NL-to-SQL → SQL validation → execution
6. **Output Guardrails** → Validate SQL, mask sensitive data
7. **Cost Tracking** → Record token usage and estimated cost
8. **Response** → Return structured response with data, charts, reports

### Guardrail Pipeline

```
Input Text
    │
    ├── Regex: Prompt Injection Patterns (17 patterns)
    ├── Regex: PII Detection (SSN, CC, email, phone)
    ├── Regex: Off-Topic Patterns (5 patterns)
    └── Length Validation
    │
    v
Generated SQL
    │
    ├── Must start with SELECT/WITH
    ├── Blocked operations: DROP, DELETE, UPDATE, INSERT, ALTER, etc.
    ├── Table allowlist: customers, products, orders, order_items, reviews, inventory_log
    ├── No multiple statements (semicolons)
    └── No SQL comments (-- or /* */)
    │
    v
Query Results
    │
    └── Sensitive column masking: email, phone, address, zip_code
```

## Key Files

| File | Purpose |
|------|---------|
| `agent/agent_workflow.py` | LangGraph state graph definition |
| `mcp_server/server.py` | FastMCP server with tool/resource definitions |
| `guardrails/input_guardrails.py` | Input safety checks |
| `guardrails/output_guardrails.py` | Output validation + data masking |
| `services/nl_to_sql_service.py` | NL-to-SQL generation with Groq |
| `utils/cost_tracker.py` | Token counting and cost estimation |
| `prompt_library/prompts.py` | All LLM prompt templates |
| `evaluation/run_evaluation.py` | Full evaluation suite entry point |
| `utils/hf_db_manager.py` | HF Dataset DB upload/download utility |
| `start.sh` | Container startup (DB download + service launch) |

## Database Schema

The e-commerce database contains 6 business tables and 1 internal table:

- **customers** (500 rows) - Customer profiles with segments
- **products** (200 rows) - Product catalog across 10 categories
- **orders** (2000 rows) - Order history over 12 months
- **order_items** (5000 rows) - Line items per order
- **reviews** (1500 rows) - Product reviews and ratings
- **inventory_log** (3000 rows) - Stock change history
- **cost_tracking** (internal) - Token usage and cost per request

## Deployment

### Architecture

```
GitHub (push to main)
    │
    ├── GitHub Actions CI/CD
    │   ├── lint (black, isort, flake8)
    │   ├── test (pytest)
    │   ├── evaluation (SQL accuracy, guardrails, routing) [non-blocking]
    │   ├── build (Docker + health check)
    │   ├── setup-hf-database (create Dataset repo, seed + upload DB)
    │   └── deploy (create Space, upload files, set secrets)
    │
    ├── HuggingFace Dataset: aniketp2009gmail/enterprise-ai-assistant-db
    │   └── ecommerce.db (seeded SQLite database)
    │
    └── HuggingFace Space: aniketp2009gmail/Enterprise-AI-Assistant-MCP
        └── Docker container
            ├── start.sh (downloads DB from Dataset → starts services)
            ├── FastAPI backend (port 8000, internal)
            ├── Streamlit frontend (port 7860, external)
            └── /data/ecommerce.db (persistent storage)
```

### CI/CD Pipeline Flow

```
lint → test ──┬── evaluation (continue-on-error, uploads artifact)
              ├── build (Docker build + health check)
              └── setup-hf-database (create Dataset, seed + upload if missing)
                       ↓
              [build + setup-hf-database]
                       ↓
                    deploy (create Space, upload files, set secrets)
```

### HuggingFace Spaces
- **Docker SDK** space with two services in one container
- FastAPI (port 8000) handles API requests internally
- Streamlit (port 7860) is the externally exposed UI
- Persistent storage at `/data` survives container restarts
- `start.sh` startup script:
  1. Detects HF Spaces environment (`/data` directory)
  2. Downloads SQLite DB from HF Dataset if not present
  3. Falls back to auto-seeding if download fails
  4. Starts FastAPI, then Streamlit

### HuggingFace Dataset
- Stores the seeded `ecommerce.db` separately from the Space
- CI/CD creates the Dataset repo and uploads DB on first deploy
- Subsequent deploys skip upload if DB already exists
- Decouples data from application code

### Database Path Resolution
- `DATABASE_PATH` env var (set by `start.sh` on HF Spaces → `/data/ecommerce.db`)
- Falls back to `config.yaml` setting (`database/ecommerce.db`)
- `DatabaseManager` auto-seeds if DB file doesn't exist at resolved path

### Secrets Management
- **GitHub Secrets**: `GROQ_API_KEY`, `HF_TOKEN` (added manually by developer)
- **HF Space Secrets**: Set automatically by CI/CD deploy job via `api.add_space_secret()`
  - `GROQ_API_KEY` — LLM inference at runtime
  - `HF_TOKEN` — downloading DB from Dataset at startup
  - `HF_DATASET_REPO` — Dataset repo identifier
