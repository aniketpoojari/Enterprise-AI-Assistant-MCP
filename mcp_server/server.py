"""MCP Server for the Enterprise AI Assistant.

Exposes e-commerce database tools via the Model Context Protocol (MCP).
Uses FastMCP for a clean, decorator-based API.
"""

from mcp.server.fastmcp import FastMCP

from mcp_server.sql_tool import SQLTool
from mcp_server.visualization_tool import VisualizationMCPTool
from mcp_server.report_tool import ReportMCPTool
from logger.logging import get_logger

logger = get_logger(__name__)

# Initialize MCP server
mcp = FastMCP(
    "ecommerce-assistant",
    instructions="Enterprise AI Assistant for e-commerce analytics. Query the database, generate charts, and create reports.",
)

# Initialize tool backends
_sql_tool = None
_viz_tool = None
_report_tool = None


def _get_sql_tool():
    global _sql_tool
    if _sql_tool is None:
        _sql_tool = SQLTool()
    return _sql_tool


def _get_viz_tool():
    global _viz_tool
    if _viz_tool is None:
        _viz_tool = VisualizationMCPTool()
    return _viz_tool


def _get_report_tool():
    global _report_tool
    if _report_tool is None:
        _report_tool = ReportMCPTool()
    return _report_tool


# --- MCP Tools ---

@mcp.tool()
def query_database(natural_language_query: str, max_rows: int = 100) -> dict:
    """Convert a natural language question about the e-commerce database into SQL,
    execute it, and return the results.

    Args:
        natural_language_query: A business question about products, orders,
            customers, reviews, or inventory. Examples:
            - "What are the top 10 best-selling products this month?"
            - "Show me revenue by category for Q4"
            - "Which customers have the highest lifetime value?"
        max_rows: Maximum number of rows to return (default 100).

    Returns:
        dict with keys: sql, columns, rows, row_count, execution_time_ms, cost
    """
    tool = _get_sql_tool()
    return tool.execute(natural_language_query, max_rows)


@mcp.tool()
def generate_chart(natural_language_query: str, chart_type: str = "bar",
                   title: str = "", x_label: str = "", y_label: str = "") -> dict:
    """Query the database and generate a chart from the results in one step.

    Args:
        natural_language_query: A business question to query and visualize.
            Examples: "top 10 products by revenue", "monthly sales trend"
        chart_type: One of 'bar', 'line', 'pie', 'scatter'. Default 'bar'.
        title: Chart title.
        x_label: X-axis label.
        y_label: Y-axis label.

    Returns:
        dict with keys: chart_base64 (PNG), chart_type, data_summary, sql, row_count
    """
    sql_tool = _get_sql_tool()
    query_result = sql_tool.execute(natural_language_query, max_rows=50)
    if query_result.get("error"):
        return {"success": False, "error": query_result["error"]}

    data = {"columns": query_result.get("columns", []), "rows": query_result.get("rows", [])}
    viz_tool = _get_viz_tool()
    chart_result = viz_tool.execute(data, chart_type, title, x_label, y_label)
    chart_result["sql"] = query_result.get("sql", "")
    chart_result["row_count"] = query_result.get("row_count", 0)
    return chart_result


@mcp.tool()
def generate_report(natural_language_query: str,
                    report_type: str = "summary") -> dict:
    """Query the database and generate a markdown report with business insights in one step.

    Args:
        natural_language_query: A business question to analyze.
            Examples: "monthly revenue trends", "customer segment breakdown"
        report_type: One of 'summary' (brief), 'detailed' (with analysis),
            'executive' (business-focused with recommendations). Default 'summary'.

    Returns:
        dict with keys: markdown, key_findings, data_quality_notes, sql, row_count
    """
    sql_tool = _get_sql_tool()
    query_result = sql_tool.execute(natural_language_query, max_rows=100)
    if query_result.get("error"):
        return {"success": False, "error": query_result["error"]}

    report_tool = _get_report_tool()
    report_result = report_tool.execute(natural_language_query, query_result, report_type)
    report_result["sql"] = query_result.get("sql", "")
    report_result["row_count"] = query_result.get("row_count", 0)
    return report_result


# --- MCP Resources ---

@mcp.resource("schema://ecommerce")
def get_database_schema() -> str:
    """Return the full database schema for context."""
    tool = _get_sql_tool()
    return tool.get_schema()


@mcp.resource("sample://ecommerce/{table_name}")
def get_sample_data(table_name: str) -> str:
    """Return sample rows from a table for context."""
    tool = _get_sql_tool()
    return tool.get_sample(table_name)


def run_server():
    """Run the MCP server with stdio transport."""
    logger.info("Starting MCP server (stdio transport)")
    mcp.run()


if __name__ == "__main__":
    run_server()
