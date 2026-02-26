"""MCP Visualization tool backend - chart generation."""

from typing import Dict, Any

from services.visualization_service import VisualizationService
from logger.logging import get_logger

logger = get_logger(__name__)


class VisualizationMCPTool:
    """Backend for the generate_chart MCP tool."""

    def __init__(self):
        try:
            self.viz_service = VisualizationService()
            logger.info("VisualizationMCPTool initialized")

        except Exception as e:
            error_msg = f"Error in VisualizationMCPTool Initialization -> {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

    def execute(self, data: Dict[str, Any], chart_type: str = "bar",
                title: str = "", x_label: str = "", y_label: str = "") -> Dict[str, Any]:
        """Generate a chart from data."""
        try:
            result = self.viz_service.generate_chart(
                data=data,
                chart_type=chart_type,
                title=title,
                x_label=x_label,
                y_label=y_label,
            )

            if result.get("error"):
                return {"success": False, "error": result["error"], "chart_base64": "", "chart_type": chart_type}

            return {
                "success": True,
                "chart_base64": result["chart_base64"],
                "chart_type": result["chart_type"],
                "data_summary": result.get("data_summary", ""),
            }

        except Exception as e:
            error_msg = f"Error in VisualizationMCPTool.execute -> {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg, "chart_base64": "", "chart_type": chart_type}
