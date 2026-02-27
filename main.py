"""FastAPI backend for the Enterprise AI Assistant."""

import asyncio
import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from agent.agent_workflow import EnterpriseAssistantWorkflow
from logger.logging import get_logger, setup_logging
from models.database import DatabaseManager
from models.pydantic_models import (
    CostInfo,
    CostSummary,
    GuardrailResult,
    GuardrailStatus,
    GuardrailTestRequest,
    HealthResponse,
    QueryIntent,
    QueryRequest,
    QueryResponse,
    SQLResult,
)
from services.cost_service import CostService
from services.guardrail_service import GuardrailService
from utils.config_loader import ConfigLoader

# Initialize logging
config = ConfigLoader()
log_level = config.get("logging.level", "INFO")
log_file = config.get("logging.file", None)
fmt = config.get("logging.format", "%(asctime)s - %(levelname)s - %(message)s")
setup_logging(log_level=log_level, log_file=log_file, format=fmt)
logger = get_logger(__name__)

# Global instances
workflow_instance = None
guardrail_service = None
cost_service = None
db_manager = None
thread_pool = ThreadPoolExecutor(max_workers=4)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    global workflow_instance, guardrail_service, cost_service, db_manager

    try:
        logger.info("Starting Enterprise AI Assistant API")
        model_provider = config.get_env("MODEL_PROVIDER", "groq")

        db_manager = DatabaseManager()
        guardrail_service = GuardrailService()
        cost_service = CostService()
        workflow_instance = EnterpriseAssistantWorkflow(
            model_provider=model_provider, guardrail_service=guardrail_service
        )
        workflow_instance.build_graph()

        logger.info("All services initialized successfully")

    except Exception as e:
        error_msg = f"Failed to initialize services: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg)

    yield

    logger.info("Shutting down Enterprise AI Assistant API")
    thread_pool.shutdown(wait=False)


app = FastAPI(
    title="Enterprise AI Assistant",
    description="AI-powered e-commerce analytics with MCP, guardrails, and cost tracking",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_workflow():
    if workflow_instance is None:
        raise HTTPException(status_code=503, detail="Workflow not initialized")
    return workflow_instance


# --- Core Endpoints ---


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest, workflow=Depends(get_workflow)):
    """Main endpoint - process a natural language query."""
    request_id = str(uuid.uuid4())
    start_time = time.time()

    try:
        loop = asyncio.get_event_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(
                thread_pool,
                lambda: workflow.invoke(request.query, request.conversation_id),
            ),
            timeout=90,
        )

        elapsed_ms = round((time.time() - start_time) * 1000, 2)

        # Build cost info
        cost_data = result.get("cost", {})
        cost = CostInfo(
            prompt_tokens=cost_data.get("prompt_tokens", 0),
            completion_tokens=cost_data.get("completion_tokens", 0),
            total_tokens=cost_data.get("total_tokens", 0),
            estimated_cost_usd=cost_data.get("estimated_cost_usd", 0),
            model_name=config.get_env("MODEL_NAME", "llama-3.1-8b-instant"),
        )

        # Build guardrail results
        guardrail_checks = []
        for gr in result.get("guardrail_results", []):
            guardrail_checks.append(
                GuardrailResult(
                    status=gr.get("status", "passed"),
                    guardrail_name=gr.get("guardrail_name", ""),
                    message=gr.get("message", ""),
                    confidence=gr.get("confidence"),
                )
            )

        # Record cost
        if db_manager:
            tools_str = json.dumps(result.get("tools_used", []))
            flags_str = json.dumps(
                [g.guardrail_name for g in guardrail_checks if g.status != "passed"]
            )
            db_manager.record_cost(
                request_id=request_id,
                query=request.query,
                model_name=cost.model_name,
                prompt_tokens=cost.prompt_tokens,
                completion_tokens=cost.completion_tokens,
                total_tokens=cost.total_tokens,
                estimated_cost_usd=cost.estimated_cost_usd,
                latency_ms=elapsed_ms,
                tools_used=tools_str,
                guardrail_flags=flags_str,
            )

        # Extract chart result if present
        chart_data = None
        if result.get("chart_result"):
            chart_data = result["chart_result"]
        elif result.get("messages"):
            # Try to find chart in tool results in message history

            from langchain_core.messages import ToolMessage

            for msg in reversed(result["messages"]):
                if isinstance(msg, ToolMessage):
                    try:
                        data = json.loads(msg.content)
                        if data.get("chart_base64"):
                            chart_data = {
                                "chart_base64": data["chart_base64"],
                                "chart_type": data.get("chart_type", "bar"),
                                "data_summary": data.get("data_summary", ""),
                            }
                            break
                    except (json.JSONDecodeError, TypeError):
                        pass

        # Extract report result if present
        report_data = None
        if result.get("report_result"):
            report_data = result["report_result"]
        elif result.get("messages"):
            # Try to find report in tool results in message history

            from langchain_core.messages import ToolMessage

            for msg in reversed(result["messages"]):
                if isinstance(msg, ToolMessage):
                    try:
                        data = json.loads(msg.content)
                        if data.get("markdown"):
                            report_data = {
                                "markdown": data["markdown"],
                                "key_findings": data.get("key_findings", []),
                                "data_quality_notes": data.get(
                                    "data_quality_notes", []
                                ),
                            }
                            break
                    except (json.JSONDecodeError, TypeError):
                        pass

        return QueryResponse(
            request_id=request_id,
            query=request.query,
            response=result.get("response", ""),
            intent=result.get("intent", "general"),
            guardrail_checks=guardrail_checks,
            cost=cost,
            tools_used=result.get("tools_used", []),
            chart=chart_data,
            report=report_data,
            execution_time_ms=elapsed_ms,
        )

    except asyncio.TimeoutError:
        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        logger.error(f"Query timed out after {elapsed_ms}ms: {request.query[:100]}")
        raise HTTPException(
            status_code=504,
            detail="Query processing timed out. Try a simpler question or try again later.",
        )
    except Exception as e:
        logger.error(f"Error processing query -> {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Guardrail Endpoints ---


@app.post("/guardrails/test")
async def test_guardrails(request: GuardrailTestRequest):
    """Test input against guardrails without executing."""
    if guardrail_service is None:
        raise HTTPException(status_code=503, detail="Guardrail service not initialized")

    result = guardrail_service.check_input(request.input)
    return result


@app.get("/guardrails/stats")
async def guardrail_stats():
    """Get guardrail trigger statistics."""
    if guardrail_service is None:
        raise HTTPException(status_code=503, detail="Guardrail service not initialized")
    return guardrail_service.get_stats()


# --- Cost Endpoints ---


@app.get("/cost/summary")
async def get_cost_summary(days: int = 30):
    """Get aggregate cost summary."""
    if cost_service is None:
        raise HTTPException(status_code=503, detail="Cost service not initialized")
    return cost_service.get_summary(days)


@app.get("/cost/history")
async def get_cost_history(limit: int = 50, offset: int = 0):
    """Get per-request cost history."""
    if cost_service is None:
        raise HTTPException(status_code=503, detail="Cost service not initialized")
    return cost_service.get_history(limit, offset)


@app.get("/cost/daily")
async def get_daily_costs(days: int = 30):
    """Get daily cost breakdown."""
    if cost_service is None:
        raise HTTPException(status_code=503, detail="Cost service not initialized")
    return cost_service.get_daily_breakdown(days)


# --- Database Endpoints ---


@app.get("/database/schema")
async def get_schema():
    """Return the database schema."""
    if db_manager is None:
        raise HTTPException(status_code=503, detail="Database not initialized")
    return {"schema": db_manager.get_schema_summary()}


@app.get("/database/tables")
async def get_tables():
    """List all available tables."""
    if db_manager is None:
        raise HTTPException(status_code=503, detail="Database not initialized")
    tables = db_manager.get_table_names()
    return {"tables": [db_manager.get_table_info(t) for t in tables]}


@app.get("/database/sample/{table_name}")
async def get_sample(table_name: str, limit: int = 5):
    """Get sample rows from a table."""
    if db_manager is None:
        raise HTTPException(status_code=503, detail="Database not initialized")
    return db_manager.get_sample_rows(table_name, limit)


# --- MCP Info ---


@app.get("/mcp/tools")
async def list_mcp_tools():
    """List available MCP tools."""
    return {
        "tools": [
            {
                "name": "query_database",
                "description": "Convert natural language to SQL and query the e-commerce database",
                "parameters": {
                    "natural_language_query": "str",
                    "max_rows": "int (default 100)",
                },
            },
            {
                "name": "generate_chart",
                "description": "Generate charts from query results",
                "parameters": {"data": "dict", "chart_type": "str", "title": "str"},
            },
            {
                "name": "generate_report",
                "description": "Generate markdown business reports from query results",
                "parameters": {
                    "query": "str",
                    "sql_result": "dict",
                    "report_type": "str",
                },
            },
        ]
    }


# --- Health ---


@app.get("/", response_model=HealthResponse)
@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    db_status = "connected" if db_manager else "disconnected"
    model_status = "loaded" if workflow_instance else "not loaded"

    return HealthResponse(
        status="ok" if workflow_instance and db_manager else "degraded",
        database=db_status,
        model=model_status,
        version="1.0.0",
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
