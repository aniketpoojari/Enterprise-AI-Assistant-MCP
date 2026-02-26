"""MCP SQL tool backend - NL-to-SQL generation and execution."""

import json
from typing import Dict, Any

from services.nl_to_sql_service import NLToSQLService
from models.database import DatabaseManager
from logger.logging import get_logger

logger = get_logger(__name__)


class SQLTool:
    """Backend for the query_database MCP tool."""

    def __init__(self):
        try:
            self.nl_to_sql = NLToSQLService()
            self.db = DatabaseManager()
            logger.info("SQLTool initialized")

        except Exception as e:
            error_msg = f"Error in SQLTool Initialization -> {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

    def execute(self, question: str, max_rows: int = 100) -> Dict[str, Any]:
        """Execute a natural language query against the database."""
        try:
            result = self.nl_to_sql.execute(question, max_rows=max_rows)

            if result.get("error"):
                return {
                    "success": False,
                    "error": result["error"],
                    "sql": result.get("sql", ""),
                    "columns": [],
                    "rows": [],
                    "row_count": 0,
                }

            return {
                "success": True,
                "sql": result["sql"],
                "columns": result["columns"],
                "rows": result["rows"],
                "row_count": result["row_count"],
                "execution_time_ms": result.get("execution_time_ms", 0),
                "truncated": result.get("truncated", False),
                "cost": result.get("cost", {}),
            }

        except Exception as e:
            error_msg = f"Error in SQLTool.execute -> {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg, "sql": "", "columns": [], "rows": [], "row_count": 0}

    def get_schema(self) -> str:
        """Return the database schema summary."""
        return self.db.get_schema_summary()

    def get_sample(self, table_name: str) -> str:
        """Return sample rows from a table as formatted text."""
        try:
            result = self.db.get_sample_rows(table_name, limit=5)
            if result.get("error"):
                return f"Error: {result['error']}"

            rows = result.get("rows", [])
            columns = result.get("columns", [])

            if not rows:
                return f"Table '{table_name}' is empty."

            lines = [f"Sample data from '{table_name}' ({len(rows)} rows):"]
            lines.append(" | ".join(columns))
            lines.append(" | ".join(["---"] * len(columns)))

            for row in rows:
                if isinstance(row, dict):
                    values = [str(row.get(c, ""))[:50] for c in columns]
                else:
                    values = [str(v)[:50] for v in row]
                lines.append(" | ".join(values))

            return "\n".join(lines)

        except Exception as e:
            return f"Error getting sample for '{table_name}': {str(e)}"
