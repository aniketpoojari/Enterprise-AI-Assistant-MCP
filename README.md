---
title: Enterprise AI Assistant MCP
emoji: 🤖
colorFrom: blue
colorTo: purple
sdk: docker
app_file: app.py
pinned: false
---

# Enterprise AI Assistant with MCP + Guardrails

An AI-powered e-commerce analytics assistant that converts natural language questions into database queries, generates charts and reports. Built with **Model Context Protocol (MCP)** for standardized tool connectivity, protected by **input/output guardrails**, and instrumented with **token cost tracking**.

## Architecture

```
User Query
    |
    v
[Input Guardrails] --> Blocked? --> Error Response
    |
    v (allowed)
[LangGraph Agent]
    |
    ├── Router --> Intent Classification (General, Query, Chart, Report)
    |
    ├── Agent Node --> LLM Logic (Groq Llama 3.1 8B)
    |
    ├── MCP Tools (FastMCP)
    |   |--- query_database   (NL-to-SQL + execution)
    |   |--- generate_chart   (matplotlib visualization)
    |   |--- generate_report  (markdown business reports)
    |
    └── Output Guardrails --> SQL validation, data masking
    |
    v
[Cost Tracker] --> Token counting, cost estimation
    |
    v
Response (with SQL, chart, report, cost info)
```

## Key Features

| Feature | Description |
|---------|-------------|
| **MCP Protocol** | Standardized tool connectivity via FastMCP (Model Context Protocol) |
| **NL-to-SQL** | Schema-aware natural language to SQL conversion with validation |
| **Input Guardrails** | Prompt injection detection, PII filtering, query validation (executed first) |
| **Output Guardrails** | SQL injection prevention, sensitive data masking, hallucination detection |
| **Cost Tracking** | Per-request token counting, cost estimation, usage dashboard |
| **Visualization** | Auto-generated charts (bar, line, pie, scatter) from query results |
| **Reports** | Markdown business reports with key findings and insights |
| **Shared Analytics** | Unified statistics for guardrails and costs across the entire application |

## Try These Questions

- "What are the top 5 products by total revenue?"
- "Show me a bar chart of revenue by product category"
- "Who are the top 3 customers by lifetime value?"
- "Generate a detailed report on sales performance"
- "Which products have less than 50 units in stock?"
- "What is the average rating for Electronics products?"
- "Show me the count of orders by status"

## Tech Stack

| Component | Technology |
|-----------|-----------|
| LLM | Groq (Llama 3.1 8B) |
| Agent Framework | LangGraph |
| Tool Protocol | MCP (FastMCP) |
| Backend | FastAPI |
| Frontend | Streamlit |
| Database | SQLite (e-commerce demo) |
| Deployment | Docker + GitHub Actions + HF Spaces |
| Evaluation | Custom eval suite (SQL accuracy, guardrails, routing) |

## Quick Start

```bash
# Clone
git clone https://github.com/aniketpoojari/Enterprise-AI-Assistant-MCP.git
cd Enterprise-AI-Assistant-MCP

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your GROQ_API_KEY

# Seed the database
python -m database.seed_data

# Start FastAPI backend (Port 8000)
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Start Streamlit frontend (Port 7860)
streamlit run app.py
```

## Docker

```bash
docker-compose up --build
```

Access: Streamlit UI at `http://localhost:7860`, API at `http://localhost:8000`, Evaluation Platform at `http://localhost:8888`

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/query` | Main NL query endpoint |
| GET | `/mcp/tools` | List available MCP tools |
| GET | `/cost/summary` | Aggregate cost summary |
| GET | `/cost/history` | Per-request cost history |
| GET | `/guardrails/stats` | Guardrail trigger statistics |
| POST | `/guardrails/test` | Test input against guardrails |
| GET | `/database/schema` | Database schema |
| GET | `/health` | Health check |

## MCP Tools

1. **query_database** - Convert natural language to SQL, execute against e-commerce database
2. **generate_chart** - Create bar/line/pie/scatter charts from query results
3. **generate_report** - Generate markdown business reports with insights

## Evaluation

```bash
# Run full evaluation suite
python -m evaluation.run_evaluation

# Run with limited queries (for CI)
EVAL_MAX_QUERIES=5 python -m evaluation.run_evaluation

# Run unit tests
pytest tests/ -v
```

## Deployment

### CI/CD Pipeline (GitHub Actions)

Pushing to `main` triggers an automated pipeline:

```
lint → test → evaluation (non-blocking) → build (Docker) → deploy (HF Spaces)
```

The pipeline also creates a **HuggingFace Dataset** (`aniketp2009gmail/enterprise-ai-assistant-db`) to store the SQLite database, and a **HuggingFace Space** (`aniketp2009gmail/Enterprise-AI-Assistant-MCP`) for the app.

### GitHub Secrets Required

| Secret | Description |
|--------|-------------|
| `GROQ_API_KEY` | Groq API key for tests, evaluations, and runtime |
| `HF_TOKEN` | HuggingFace token (write access) for deployment |

### How It Works

1. **CI**: Lint → Unit tests → Evaluation suite (limited queries, non-blocking)
2. **Build**: Docker image build + health check
3. **Database**: Seeds SQLite DB and uploads to HF Dataset (if not already present)
4. **Deploy**: Uploads project to HF Space, sets runtime secrets automatically
5. **Startup**: Container downloads DB from HF Dataset → starts FastAPI + Streamlit

### Live Demo

- **App**: [huggingface.co/spaces/aniketp2009gmail/Enterprise-AI-Assistant-MCP](https://huggingface.co/spaces/aniketp2009gmail/Enterprise-AI-Assistant-MCP)
- **Database**: [huggingface.co/datasets/aniketp2009gmail/enterprise-ai-assistant-db](https://huggingface.co/datasets/aniketp2009gmail/enterprise-ai-assistant-db)

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | Yes | Groq API key |
| `MODEL_NAME` | No | Model name (default: llama-3.1-8b-instant) |
| `MODEL_PROVIDER` | No | LLM provider (default: groq) |
| `HF_TOKEN` | Deploy | HuggingFace token for DB download and deployment |
| `HF_DATASET_REPO` | Deploy | HF Dataset repo ID (default: aniketp2009gmail/enterprise-ai-assistant-db) |
| `DATABASE_PATH` | No | Override database file path (auto-set on HF Spaces) |
| `LANGCHAIN_API_KEY` | No | LangSmith API key for tracing |

## Project Structure

```
Enterprise-AI-Assistant-MCP/
├── .github/workflows/  # CI/CD pipeline (lint → test → eval → build → deploy)
├── agent/              # LangGraph workflow (Router → Agent → Tools → Critic)
├── config/             # YAML configs (app + guardrails)
├── database/           # SQLite schema + seed data (e-commerce demo)
├── evaluation/         # SQL accuracy, guardrail, and agent decision evals
├── guardrails/         # Input/output guardrails (injection, PII, SQL validation)
├── logger/             # Logging setup
├── mcp_server/         # MCP server (FastMCP) with 3 tools + 2 resources
├── models/             # Pydantic models + database manager
├── prompt_library/     # All prompt templates
├── services/           # NL-to-SQL, visualization, reports, cost, guardrails
├── tests/              # Unit tests
├── tools/              # LangChain @tool wrappers for LangGraph
├── utils/              # Config loader, model loader, cost tracker, SQL utils, HF DB manager
├── app.py              # Streamlit frontend
├── main.py             # FastAPI backend
├── start.sh            # Container startup (DB download + service startup)
├── Dockerfile          # Multi-stage Docker build
└── docker-compose.yaml # Local development
```

## License

MIT
