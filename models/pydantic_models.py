"""Pydantic models for data validation and serialization."""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator
from enum import Enum


class QueryIntent(str, Enum):
    """Types of user query intents."""
    SQL_QUERY = "sql_query"
    VISUALIZATION = "visualization"
    REPORT = "report"
    GENERAL = "general"


class GuardrailStatus(str, Enum):
    """Guardrail check status."""
    PASSED = "passed"
    BLOCKED = "blocked"
    WARNING = "warning"


class ChartType(str, Enum):
    """Supported chart types."""
    BAR = "bar"
    LINE = "line"
    PIE = "pie"
    SCATTER = "scatter"
    HEATMAP = "heatmap"


class ReportType(str, Enum):
    """Report generation types."""
    SUMMARY = "summary"
    DETAILED = "detailed"
    EXECUTIVE = "executive"


# --- Request Models ---

class QueryRequest(BaseModel):
    """Model for incoming user queries."""
    query: str = Field(..., description="Natural language question about the business")
    conversation_id: Optional[str] = Field(None, description="Conversation session ID")
    max_results: Optional[int] = Field(100, description="Maximum number of data rows to return")

    @field_validator('query')
    @classmethod
    def query_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Query cannot be empty')
        return v.strip()


class GuardrailTestRequest(BaseModel):
    """Model for testing input against guardrails."""
    input: str = Field(..., description="Text to test against guardrails")


# --- Response Models ---

class GuardrailResult(BaseModel):
    """Result of a guardrail check."""
    status: GuardrailStatus = Field(..., description="Check status")
    guardrail_name: str = Field(..., description="Name of the guardrail")
    message: str = Field("", description="Details about the check")
    confidence: Optional[float] = Field(None, description="Confidence score 0.0-1.0")


class SQLResult(BaseModel):
    """Result of SQL query execution."""
    sql: str = Field(..., description="The generated SQL query")
    columns: List[str] = Field(default_factory=list, description="Column names")
    rows: List[Dict[str, Any]] = Field(default_factory=list, description="Result rows")
    row_count: int = Field(0, description="Number of rows returned")
    execution_time_ms: float = Field(0, description="Query execution time in ms")
    truncated: bool = Field(False, description="Whether results were truncated")


class ChartResult(BaseModel):
    """Result of chart generation."""
    chart_base64: str = Field(..., description="Base64-encoded PNG image")
    chart_type: str = Field(..., description="Chart type used")
    data_summary: str = Field("", description="Brief text summary of the data")


class ReportResult(BaseModel):
    """Result of report generation."""
    markdown: str = Field(..., description="Report in markdown format")
    key_findings: List[str] = Field(default_factory=list, description="Bullet-point findings")
    data_quality_notes: List[str] = Field(default_factory=list, description="Data caveats")


class CostInfo(BaseModel):
    """Token and cost information for a request."""
    prompt_tokens: int = Field(0, description="Input tokens used")
    completion_tokens: int = Field(0, description="Output tokens generated")
    total_tokens: int = Field(0, description="Total tokens used")
    estimated_cost_usd: float = Field(0, description="Estimated cost in USD")
    model_name: str = Field("", description="Model used")


class QueryResponse(BaseModel):
    """Complete response for a user query."""
    request_id: str = Field(..., description="Unique request identifier")
    query: str = Field(..., description="Original user query")
    response: str = Field(..., description="Natural language response")
    intent: QueryIntent = Field(..., description="Detected query intent")
    sql_result: Optional[SQLResult] = Field(None, description="SQL query result if applicable")
    chart: Optional[ChartResult] = Field(None, description="Generated chart if applicable")
    report: Optional[ReportResult] = Field(None, description="Generated report if applicable")
    guardrail_checks: List[GuardrailResult] = Field(default_factory=list, description="Guardrail results")
    cost: CostInfo = Field(default_factory=CostInfo, description="Token usage and cost")
    tools_used: List[str] = Field(default_factory=list, description="MCP tools invoked")
    execution_time_ms: float = Field(0, description="Total execution time in ms")
    created_at: datetime = Field(default_factory=datetime.now, description="Response timestamp")

    model_config = ConfigDict(use_enum_values=True)


class CostSummary(BaseModel):
    """Aggregate cost summary."""
    total_requests: int = Field(0, description="Total number of requests")
    total_tokens: int = Field(0, description="Total tokens used")
    total_cost_usd: float = Field(0, description="Total estimated cost")
    avg_tokens_per_request: float = Field(0, description="Average tokens per request")
    avg_cost_per_request: float = Field(0, description="Average cost per request")
    avg_latency_ms: float = Field(0, description="Average latency")
    period_start: Optional[str] = Field(None, description="Start of period")
    period_end: Optional[str] = Field(None, description="End of period")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field("ok", description="Service status")
    database: str = Field("", description="Database status")
    model: str = Field("", description="Model status")
    version: str = Field("1.0.0", description="API version")
