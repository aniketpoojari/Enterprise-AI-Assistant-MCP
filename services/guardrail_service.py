"""Guardrail orchestration service - coordinates input and output guardrails."""

from typing import Any, Dict, List

from guardrails.input_guardrails import InputGuardrails
from guardrails.output_guardrails import OutputGuardrails
from logger.logging import get_logger

logger = get_logger(__name__)


class GuardrailService:
    """Orchestrates input and output guardrails."""

    def __init__(self):
        try:
            self.input_guardrails = InputGuardrails()
            self.output_guardrails = OutputGuardrails()
            self._stats = {"total_checks": 0, "blocks": 0, "warnings": 0, "passes": 0}
            logger.info("GuardrailService initialized")

        except Exception as e:
            error_msg = f"Error in GuardrailService Initialization -> {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

    def check_input(self, user_input: str) -> Dict[str, Any]:
        """Run all input guardrails.

        Returns:
            Dict with: allowed (bool), results (list), block_reason (str)
        """
        results = self.input_guardrails.check_all(user_input)
        is_blocked = self.input_guardrails.is_blocked(results)
        block_reason = (
            self.input_guardrails.get_block_reason(results) if is_blocked else ""
        )

        # Update stats
        self._stats["total_checks"] += 1
        for r in results:
            if r["status"] == "blocked":
                self._stats["blocks"] += 1
            elif r["status"] == "warning":
                self._stats["warnings"] += 1
            else:
                self._stats["passes"] += 1

        return {
            "allowed": not is_blocked,
            "results": results,
            "block_reason": block_reason,
        }

    def check_output(
        self,
        sql: str = "",
        rows: List[Dict] = None,
        columns: List[str] = None,
        response_text: str = "",
    ) -> Dict[str, Any]:
        """Run all output guardrails.

        Returns:
            Dict with: allowed (bool), results (list), masked_rows (list)
        """
        results = self.output_guardrails.check_all(
            sql=sql, rows=rows, columns=columns, response_text=response_text
        )
        is_blocked = self.output_guardrails.is_blocked(results)

        # Mask sensitive data in results
        masked_rows = rows
        if rows and columns:
            masked_rows = self.output_guardrails.mask_sensitive_data(rows, columns)

        return {
            "allowed": not is_blocked,
            "results": results,
            "masked_rows": masked_rows,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get guardrail trigger statistics."""
        return dict(self._stats)
