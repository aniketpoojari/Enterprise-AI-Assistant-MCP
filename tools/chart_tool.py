"""LangChain tool wrapper for chart generation - used by LangGraph agent."""

from langchain_core.tools import tool

from logger.logging import get_logger
from mcp_server.sql_tool import SQLTool
from mcp_server.visualization_tool import VisualizationMCPTool

logger = get_logger(__name__)

_viz_tool = None
_sql_tool = None


def _get_viz_tool():
    global _viz_tool
    if _viz_tool is None:
        _viz_tool = VisualizationMCPTool()
    return _viz_tool


def _get_sql_tool():
    global _sql_tool
    if _sql_tool is None:
        _sql_tool = SQLTool()
    return _sql_tool


@tool
def generate_chart(
    natural_language_query: str,
    chart_type: str = "bar",
    title: str = "",
    x_label: str = "",
    y_label: str = "",
) -> dict:
    """Query data and generate a chart (bar, line, pie, or scatter).

    Args:
        natural_language_query: Question about data (e.g. "revenue by category")
        chart_type: The type of chart: 'bar', 'line', 'pie', or 'scatter'
        title: Optional chart title
        x_label: Optional X-axis label
        y_label: Optional Y-axis label
    """
    try:
        # Step 1: Query the database
        query_result = _get_sql_tool().execute(natural_language_query, max_rows=50)
        if query_result.get("error"):
            return {"success": False, "error": query_result["error"]}

        data = {
            "columns": query_result.get("columns", []),
            "rows": query_result.get("rows", []),
        }

        # Step 2: Generate the chart
        chart_result = _get_viz_tool().execute(
            data, chart_type, title, x_label, y_label
        )
        chart_result["sql"] = query_result.get("sql", "")
        chart_result["row_count"] = query_result.get("row_count", 0)
        return chart_result

    except Exception as e:
        logger.error(f"Error in generate_chart -> {str(e)}")
        return {"success": False, "error": str(e)}
