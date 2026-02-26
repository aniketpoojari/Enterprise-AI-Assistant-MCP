"""Report generation service for the Enterprise AI Assistant."""

import json
from typing import Any, Dict, List

from logger.logging import get_logger
from prompt_library.prompts import REPORT_SYSTEM_PROMPT, REPORT_USER_PROMPT
from utils.cost_tracker import CostTracker
from utils.model_loader import ModelLoader

logger = get_logger(__name__)


class ReportService:
    """Generates markdown reports from query results with business insights."""

    def __init__(self, model_provider: str = "groq"):
        try:
            self.model_loader = ModelLoader(model_provider)
            self.llm = self.model_loader.load_llm()
            self.cost_tracker = CostTracker()
            logger.info("ReportService initialized")

        except Exception as e:
            error_msg = f"Error in ReportService Initialization -> {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

    def generate(
        self,
        question: str,
        sql: str,
        data: Dict[str, Any],
        report_type: str = "summary",
    ) -> Dict[str, Any]:
        """Generate a markdown report from query results.

        Args:
            question: Original natural language question
            sql: The SQL query that was executed
            data: Query result with 'columns' and 'rows'
            report_type: 'summary', 'detailed', or 'executive'

        Returns:
            Dict with markdown, key_findings, data_quality_notes, cost
        """
        try:
            rows = data.get("rows", [])
            columns = data.get("columns", [])
            row_count = data.get("row_count", len(rows))

            # Format data preview (limit to keep prompt manageable)
            preview_rows = rows[:20]
            data_preview = self._format_data_preview(columns, preview_rows)

            from langchain_core.messages import HumanMessage, SystemMessage

            messages = [
                SystemMessage(content=REPORT_SYSTEM_PROMPT),
                HumanMessage(
                    content=REPORT_USER_PROMPT.format(
                        report_type=report_type,
                        question=question,
                        sql=sql,
                        row_count=row_count,
                        data_preview=data_preview,
                    )
                ),
            ]

            response = self.llm.invoke(messages)
            cost_info = self.cost_tracker.track_call(response)

            # Parse response
            markdown = response.content
            key_findings = self._extract_findings(markdown)
            data_quality_notes = self._extract_quality_notes(markdown, rows, columns)

            return {
                "markdown": markdown,
                "key_findings": key_findings,
                "data_quality_notes": data_quality_notes,
                "cost": cost_info,
            }

        except Exception as e:
            error_msg = f"Error generating report -> {str(e)}"
            logger.error(error_msg)
            return {
                "markdown": f"Error generating report: {error_msg}",
                "key_findings": [],
                "data_quality_notes": [],
                "cost": {},
            }

    def _format_data_preview(self, columns: List[str], rows: List[Dict]) -> str:
        """Format query results as a readable table for the LLM with truncation."""
        if not rows:
            return "No data returned."

        # Header
        lines = [" | ".join(columns)]
        lines.append(" | ".join(["---"] * len(columns)))

        # Rows (limit each value to keep prompt manageable)
        for row in rows:
            if isinstance(row, dict):
                # Truncate each value to 200 chars to avoid huge prompts if cells have long text
                values = [str(row.get(col, ""))[:200] + ("..." if len(str(row.get(col, ""))) > 200 else "") for col in columns]
            else:
                values = [str(v)[:200] + ("..." if len(str(v)) > 200 else "") for v in row]
            lines.append(" | ".join(values))
            
            # If total length is already too large, stop adding rows
            if sum(len(line) for line in lines) > 8000:
                lines.append("... [Additional rows omitted for brevity]")
                break

        return "\n".join(lines)

    def _extract_findings(self, markdown: str) -> List[str]:
        """Extract key findings bullet points from the report markdown."""
        findings = []
        in_findings = False

        for line in markdown.split("\n"):
            stripped = line.strip()
            if (
                "finding" in stripped.lower()
                or "insight" in stripped.lower()
                or "key" in stripped.lower()
            ):
                in_findings = True
                continue
            if in_findings and stripped.startswith(("-", "*", "•")):
                findings.append(stripped.lstrip("-*• ").strip())
            elif in_findings and stripped.startswith("#"):
                in_findings = False

        # Fallback: extract all bullet points
        if not findings:
            for line in markdown.split("\n"):
                stripped = line.strip()
                if stripped.startswith(("-", "*", "•")) and len(stripped) > 10:
                    findings.append(stripped.lstrip("-*• ").strip())

        return findings[:5]

    def _extract_quality_notes(
        self, markdown: str, rows: List, columns: List
    ) -> List[str]:
        """Generate data quality notes."""
        notes = []

        if not rows:
            notes.append("No data returned for this query.")
        elif len(rows) >= 100:
            notes.append(
                "Results were truncated to 100 rows. The full dataset may contain more records."
            )

        # Check for NULL values
        if rows and isinstance(rows[0], dict):
            for col in columns:
                null_count = sum(1 for row in rows if row.get(col) is None)
                if null_count > 0:
                    notes.append(
                        f"Column '{col}' has {null_count} NULL values ({null_count}/{len(rows)} rows)."
                    )

        return notes
