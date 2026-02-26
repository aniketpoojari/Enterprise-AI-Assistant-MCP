"""Output guardrails - validate and sanitize responses before returning to user."""

import json
import re
from pathlib import Path
from typing import Any, Dict, List

import yaml

from guardrails.patterns import DATA_MASKING_PATTERNS, SQL_INJECTION_PATTERNS
from logger.logging import get_logger
from utils.sql_utils import validate_sql

logger = get_logger(__name__)


class OutputGuardrails:
    """Validates and sanitizes output before returning to the user."""

    def __init__(
        self,
        config_path: str = None,
    ):
        if config_path is None:
            config_path = str(
                Path(__file__).parent.parent / "config" / "guardrails_config.yaml"
            )
        try:
            self.config = self._load_config(config_path)
            self.output_config = self.config.get("output_guardrails", {})

            masking_config = self.output_config.get("data_masking", {})
            self.sensitive_columns = set(masking_config.get("sensitive_columns", []))
            self.masking_char = masking_config.get("masking_char", "*")
            self.visible_chars = masking_config.get("visible_chars", 3)

            logger.info("OutputGuardrails initialized")

        except Exception as e:
            error_msg = f"Error in OutputGuardrails Initialization -> {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

    def _load_config(self, config_path: str) -> Dict:
        """Load guardrails configuration."""
        path = Path(config_path)
        if path.exists():
            with open(path, "r") as f:
                return yaml.safe_load(f) or {}
        return {}

    def check_all(
        self,
        sql: str = "",
        rows: List[Dict] = None,
        columns: List[str] = None,
        response_text: str = "",
    ) -> List[Dict[str, Any]]:
        """Run all output guardrails.

        Returns:
            List of guardrail check results.
        """
        results = []

        # 1. SQL validation
        if sql and self.output_config.get("sql_validation", {}).get("enabled", True):
            results.append(self.check_sql_safety(sql))

        # 2. Additional SQL injection patterns
        if sql:
            results.append(self.check_sql_injection_patterns(sql))

        return results

    def is_blocked(self, results: List[Dict[str, Any]]) -> bool:
        """Check if any output guardrail blocked the response."""
        return any(r["status"] == "blocked" for r in results)

    def check_sql_safety(self, sql: str) -> Dict[str, Any]:
        """Validate generated SQL against safety rules."""
        allowed_tables = self.output_config.get("sql_validation", {}).get(
            "allowed_tables", []
        )

        is_valid, error_msg = validate_sql(
            sql, allowed_tables if allowed_tables else None
        )

        if not is_valid:
            logger.warning(f"SQL safety check failed: {error_msg}")
            return {
                "guardrail_name": "sql_validation",
                "status": "blocked",
                "message": f"Generated SQL failed safety validation: {error_msg}",
                "confidence": 1.0,
            }

        return {
            "guardrail_name": "sql_validation",
            "status": "passed",
            "message": "SQL passed safety validation",
            "confidence": 1.0,
        }

    def check_sql_injection_patterns(self, sql: str) -> Dict[str, Any]:
        """Check for SQL injection patterns in generated SQL."""
        for pattern in SQL_INJECTION_PATTERNS:
            if pattern.search(sql):
                logger.warning(f"SQL injection pattern detected in output")
                return {
                    "guardrail_name": "sql_injection_check",
                    "status": "blocked",
                    "message": "Suspicious SQL pattern detected in generated query.",
                    "confidence": 0.95,
                }

        return {
            "guardrail_name": "sql_injection_check",
            "status": "passed",
            "message": "No SQL injection patterns detected",
            "confidence": 1.0,
        }

    def mask_sensitive_data(self, rows: List[Dict], columns: List[str]) -> List[Dict]:
        """Mask sensitive columns in query results."""
        if not rows or not self.output_config.get("data_masking", {}).get(
            "enabled", True
        ):
            return rows

        cols_to_mask = self.sensitive_columns.intersection(set(columns))
        if not cols_to_mask:
            return rows

        masked_rows = []
        for row in rows:
            masked_row = dict(row)
            for col in cols_to_mask:
                if col in masked_row and masked_row[col]:
                    value = str(masked_row[col])
                    if len(value) > self.visible_chars:
                        masked_row[col] = value[
                            : self.visible_chars
                        ] + self.masking_char * (len(value) - self.visible_chars)
                    else:
                        masked_row[col] = self.masking_char * len(value)
            masked_rows.append(masked_row)

        return masked_rows
