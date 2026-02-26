"""SQLite database connection manager for the Enterprise AI Assistant."""

import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from logger.logging import get_logger
from utils.config_loader import ConfigLoader

logger = get_logger(__name__)


class DatabaseManager:
    """Manages SQLite database connections and operations."""

    def __init__(self):
        try:
            self.config = ConfigLoader()
            self.db_path = os.environ.get(
                "DATABASE_PATH",
                self.config.get("database.path", "database/ecommerce.db"),
            )
            self._ensure_db_exists()
            logger.info(f"DatabaseManager initialized with {self.db_path}")

        except Exception as e:
            error_msg = f"Error in DatabaseManager Initialization -> {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

    def _ensure_db_exists(self):
        """Create and seed database if it doesn't exist."""
        db_file = Path(self.db_path)
        if not db_file.exists():
            logger.info("Database not found, creating and seeding...")
            from database.seed_data import seed_database

            seed_database(self.db_path)

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def execute_query(
        self, sql: str, params: tuple = (), max_rows: int = 100
    ) -> Dict[str, Any]:
        """Execute a SELECT query and return results."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            import time

            start = time.time()
            cursor.execute(sql, params)
            rows = cursor.fetchmany(max_rows)
            elapsed_ms = round((time.time() - start) * 1000, 2)

            columns = (
                [desc[0] for desc in cursor.description] if cursor.description else []
            )
            data = [dict(row) for row in rows]

            conn.close()

            return {
                "columns": columns,
                "rows": data,
                "row_count": len(data),
                "execution_time_ms": elapsed_ms,
                "sql": sql,
                "truncated": len(data) == max_rows,
            }

        except Exception as e:
            error_msg = f"Error executing query -> {str(e)}"
            logger.error(error_msg)
            return {
                "error": error_msg,
                "sql": sql,
                "rows": [],
                "columns": [],
                "row_count": 0,
            }

    def get_schema(self) -> str:
        """Return the full database schema as DDL."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND sql IS NOT NULL ORDER BY name"
            )
            tables = cursor.fetchall()

            schema_parts = []
            for table in tables:
                schema_parts.append(table["sql"] + ";")

            conn.close()
            return "\n\n".join(schema_parts)

        except Exception as e:
            error_msg = f"Error getting schema -> {str(e)}"
            logger.error(error_msg)
            return ""

    def get_table_names(self) -> List[str]:
        """Return list of table names."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
            tables = [row["name"] for row in cursor.fetchall()]
            conn.close()
            return tables

        except Exception as e:
            logger.error(f"Error getting table names -> {str(e)}")
            return []

    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """Get detailed info about a table."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Column info
            cursor.execute(f"PRAGMA table_info('{table_name}')")
            columns = [
                {
                    "name": r["name"],
                    "type": r["type"],
                    "notnull": r["notnull"],
                    "pk": r["pk"],
                }
                for r in cursor.fetchall()
            ]

            # Row count
            cursor.execute(f"SELECT COUNT(*) as count FROM '{table_name}'")
            row_count = cursor.fetchone()["count"]

            conn.close()

            return {
                "table_name": table_name,
                "columns": columns,
                "row_count": row_count,
            }

        except Exception as e:
            logger.error(f"Error getting table info for {table_name} -> {str(e)}")
            return {
                "table_name": table_name,
                "columns": [],
                "row_count": 0,
                "error": str(e),
            }

    def get_sample_rows(self, table_name: str, limit: int = 5) -> Dict[str, Any]:
        """Get sample rows from a table."""
        return self.execute_query(
            f"SELECT * FROM '{table_name}' LIMIT ?", (limit,), max_rows=limit
        )

    def get_schema_summary(self) -> str:
        """Get a formatted schema summary with table info and sample data for LLM context."""
        try:
            tables = self.get_table_names()
            # Exclude internal tables
            tables = [t for t in tables if t != "cost_tracking"]

            summary_parts = ["## E-Commerce Database Schema\n"]

            for table in tables:
                info = self.get_table_info(table)
                summary_parts.append(f"### Table: {table} ({info['row_count']} rows)")

                col_lines = []
                for col in info["columns"]:
                    pk = " [PK]" if col["pk"] else ""
                    nn = " NOT NULL" if col["notnull"] else ""
                    col_lines.append(f"  - {col['name']} ({col['type']}{pk}{nn})")
                summary_parts.append("\n".join(col_lines))

                # Sample data
                sample = self.get_sample_rows(table, limit=3)
                if sample.get("rows"):
                    summary_parts.append(f"  Sample: {sample['rows'][:2]}")

                summary_parts.append("")

            return "\n".join(summary_parts)

        except Exception as e:
            logger.error(f"Error getting schema summary -> {str(e)}")
            return "Error loading schema"

    def record_cost(
        self,
        request_id: str,
        query: str,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        estimated_cost_usd: float,
        latency_ms: float = None,
        tools_used: str = None,
        guardrail_flags: str = None,
        success: bool = True,
    ):
        """Record a cost tracking entry."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO cost_tracking
                   (request_id, query, model_name, prompt_tokens, completion_tokens,
                    total_tokens, estimated_cost_usd, latency_ms, tools_used, guardrail_flags, success)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    request_id,
                    query,
                    model_name,
                    prompt_tokens,
                    completion_tokens,
                    total_tokens,
                    estimated_cost_usd,
                    latency_ms,
                    tools_used,
                    guardrail_flags,
                    success,
                ),
            )
            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Error recording cost -> {str(e)}")
