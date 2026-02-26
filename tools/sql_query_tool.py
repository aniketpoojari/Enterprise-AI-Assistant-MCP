"""LangChain tool wrapper for SQL queries - used by LangGraph agent."""

from langchain_core.tools import tool

from logger.logging import get_logger
from mcp_server.sql_tool import SQLTool

logger = get_logger(__name__)

_sql_tool = None
_sql_tool_init_failed = False


def _get_tool():
    global _sql_tool, _sql_tool_init_failed
    if _sql_tool is None:
        _sql_tool_init_failed = False
        _sql_tool = SQLTool()
    return _sql_tool


@tool
def query_database(natural_language_query: str, max_rows: int = 100) -> dict:
    """Query the database using a natural language question.

    Args:
        natural_language_query: Question about data (e.g. "top 5 products")
        max_rows: Max number of rows to return (default 100)
    """
    return _get_tool().execute(natural_language_query, max_rows)
