"""LangChain tool wrapper for report generation - used by LangGraph agent."""

from langchain_core.tools import tool

from logger.logging import get_logger
from mcp_server.report_tool import ReportMCPTool
from mcp_server.sql_tool import SQLTool

logger = get_logger(__name__)

_report_tool = None
_sql_tool = None


def _get_report_tool():
    global _report_tool
    if _report_tool is None:
        _report_tool = ReportMCPTool()
    return _report_tool


def _get_sql_tool():
    global _sql_tool
    if _sql_tool is None:
        _sql_tool = SQLTool()
    return _sql_tool


@tool
def generate_report(natural_language_query: str, report_type: str = "summary") -> dict:
    """Query data and generate a business report (summary, detailed, or executive).

    Args:
        natural_language_query: Question about data (e.g. "sales analysis")
        report_type: The type of report: 'summary', 'detailed', or 'executive'
    """
    try:
        # Step 1: Query the database
        query_result = _get_sql_tool().execute(natural_language_query, max_rows=100)
        if query_result.get("error"):
            return {"success": False, "error": query_result["error"]}

        # Step 2: Generate the report
        report_result = _get_report_tool().execute(
            natural_language_query, query_result, report_type
        )
        report_result["sql"] = query_result.get("sql", "")
        report_result["row_count"] = query_result.get("row_count", 0)
        return report_result

    except Exception as e:
        logger.error(f"Error in generate_report -> {str(e)}")
        return {"success": False, "error": str(e)}
