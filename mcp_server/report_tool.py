"""MCP Report tool backend - report generation."""

from typing import Any, Dict

from logger.logging import get_logger
from services.report_service import ReportService

logger = get_logger(__name__)


class ReportMCPTool:
    """Backend for the generate_report MCP tool."""

    def __init__(self):
        try:
            self.report_service = ReportService()
            logger.info("ReportMCPTool initialized")

        except Exception as e:
            error_msg = f"Error in ReportMCPTool Initialization -> {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

    def execute(
        self, query: str, sql_result: Dict[str, Any], report_type: str = "summary"
    ) -> Dict[str, Any]:
        """Generate a report from query results."""
        try:
            sql = sql_result.get("sql", "")
            result = self.report_service.generate(
                question=query,
                sql=sql,
                data=sql_result,
                report_type=report_type,
            )

            if "Error" in result.get("markdown", ""):
                return {
                    "success": False,
                    "error": result["markdown"],
                    "markdown": "",
                    "key_findings": [],
                }

            return {
                "success": True,
                "markdown": result["markdown"],
                "key_findings": result["key_findings"],
                "data_quality_notes": result.get("data_quality_notes", []),
                "cost": result.get("cost", {}),
            }

        except Exception as e:
            error_msg = f"Error in ReportMCPTool.execute -> {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "markdown": "",
                "key_findings": [],
            }
