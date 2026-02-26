"""Cost tracking and analytics service."""

import os
import sqlite3
from typing import Any, Dict, List, Optional

from logger.logging import get_logger
from utils.config_loader import ConfigLoader

logger = get_logger(__name__)


class CostService:
    """Provides cost analytics and usage summaries."""

    def __init__(self):
        try:
            self.config = ConfigLoader()
            self.db_path = os.environ.get(
                "DATABASE_PATH",
                self.config.get("database.path", "database/ecommerce.db"),
            )
            logger.info("CostService initialized")

        except Exception as e:
            error_msg = f"Error in CostService Initialization -> {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_summary(self, days: int = 30) -> Dict[str, Any]:
        """Get aggregate cost summary for the specified period."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    COUNT(*) as total_requests,
                    COALESCE(SUM(total_tokens), 0) as total_tokens,
                    COALESCE(SUM(estimated_cost_usd), 0) as total_cost_usd,
                    COALESCE(AVG(total_tokens), 0) as avg_tokens_per_request,
                    COALESCE(AVG(estimated_cost_usd), 0) as avg_cost_per_request,
                    COALESCE(AVG(latency_ms), 0) as avg_latency_ms,
                    MIN(created_at) as period_start,
                    MAX(created_at) as period_end
                FROM cost_tracking
                WHERE created_at >= datetime('now', ?)
            """,
                (f"-{days} days",),
            )

            row = cursor.fetchone()
            conn.close()

            return {
                "total_requests": row["total_requests"],
                "total_tokens": row["total_tokens"],
                "total_cost_usd": round(row["total_cost_usd"], 6),
                "avg_tokens_per_request": round(row["avg_tokens_per_request"], 1),
                "avg_cost_per_request": round(row["avg_cost_per_request"], 8),
                "avg_latency_ms": round(row["avg_latency_ms"], 1),
                "period_start": row["period_start"],
                "period_end": row["period_end"],
            }

        except Exception as e:
            logger.error(f"Error getting cost summary -> {str(e)}")
            return {"total_requests": 0, "total_tokens": 0, "total_cost_usd": 0}

    def get_history(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get per-request cost history."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT request_id, query, model_name, prompt_tokens, completion_tokens,
                       total_tokens, estimated_cost_usd, latency_ms, tools_used,
                       guardrail_flags, success, created_at
                FROM cost_tracking
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """,
                (limit, offset),
            )

            rows = [dict(r) for r in cursor.fetchall()]
            conn.close()
            return rows

        except Exception as e:
            logger.error(f"Error getting cost history -> {str(e)}")
            return []

    def get_daily_breakdown(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get daily cost breakdown for charts."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    DATE(created_at) as date,
                    COUNT(*) as requests,
                    SUM(total_tokens) as tokens,
                    SUM(estimated_cost_usd) as cost_usd,
                    AVG(latency_ms) as avg_latency_ms
                FROM cost_tracking
                WHERE created_at >= datetime('now', ?)
                GROUP BY DATE(created_at)
                ORDER BY date
            """,
                (f"-{days} days",),
            )

            rows = [dict(r) for r in cursor.fetchall()]
            conn.close()
            return rows

        except Exception as e:
            logger.error(f"Error getting daily breakdown -> {str(e)}")
            return []
