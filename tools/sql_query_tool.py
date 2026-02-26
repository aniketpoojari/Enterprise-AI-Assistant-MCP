"""LangChain tool wrapper for SQL queries - used by LangGraph agent."""

from langchain_core.tools import tool
from mcp_server.sql_tool import SQLTool
from logger.logging import get_logger

logger = get_logger(__name__)

_sql_tool = None


def _get_tool():
    global _sql_tool
    if _sql_tool is None:
        _sql_tool = SQLTool()
    return _sql_tool


@tool
def query_database(natural_language_query: str, max_rows: int = 100) -> dict:
    """Query the e-commerce database with a natural language question.

    Use this tool to answer any question about products, orders, customers,
    reviews, or inventory. The tool converts your question to SQL and returns results.

    Args:
        natural_language_query: Business question (e.g., "top 10 products by revenue")
        max_rows: Maximum rows to return (default 100)

    Returns:
        Dict with sql, columns, rows, row_count
    """
    return _get_tool().execute(natural_language_query, max_rows)
