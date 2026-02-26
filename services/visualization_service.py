"""Chart generation service for the Enterprise AI Assistant."""

import io
import base64
from typing import Dict, Any, List

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for server use
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

from logger.logging import get_logger

logger = get_logger(__name__)


class VisualizationService:
    """Generates charts from query result data."""

    def __init__(self):
        try:
            plt.style.use('seaborn-v0_8-whitegrid')
            logger.info("VisualizationService initialized")

        except Exception as e:
            error_msg = f"Error in VisualizationService Initialization -> {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

    def generate_chart(self, data: Dict[str, Any], chart_type: str = "bar",
                       title: str = "", x_label: str = "", y_label: str = "") -> Dict[str, Any]:
        """Generate a chart from query result data.

        Args:
            data: Dict with 'columns' and 'rows' from query results.
            chart_type: 'bar', 'line', 'pie', 'scatter', 'heatmap'
            title: Chart title
            x_label: X-axis label
            y_label: Y-axis label

        Returns:
            Dict with chart_base64, chart_type, data_summary
        """
        try:
            columns = data.get("columns", [])
            rows = data.get("rows", [])

            if not rows or not columns:
                return {"error": "No data to visualize", "chart_base64": "", "chart_type": chart_type}

            # Auto-detect x and y columns if not enough info
            x_col, y_cols = self._detect_axes(columns, rows)

            if not x_label:
                x_label = x_col
            if not y_label and y_cols:
                y_label = y_cols[0]

            # Extract data
            x_data = [row[x_col] if isinstance(row, dict) else row[0] for row in rows]
            y_data_dict = {}
            for y_col in y_cols:
                y_data_dict[y_col] = [
                    float(row[y_col]) if isinstance(row, dict) else float(row[columns.index(y_col)])
                    for row in rows
                ]

            # Create chart
            fig, ax = plt.subplots(figsize=(10, 6))

            if chart_type == "bar":
                self._create_bar_chart(ax, x_data, y_data_dict, y_cols)
            elif chart_type == "line":
                self._create_line_chart(ax, x_data, y_data_dict, y_cols)
            elif chart_type == "pie":
                self._create_pie_chart(ax, x_data, list(y_data_dict.values())[0] if y_data_dict else [])
            elif chart_type == "scatter":
                self._create_scatter_chart(ax, x_data, y_data_dict, y_cols)
            else:
                self._create_bar_chart(ax, x_data, y_data_dict, y_cols)

            ax.set_title(title or f"{y_label} by {x_label}", fontsize=14, fontweight='bold')
            if chart_type != "pie":
                ax.set_xlabel(x_label, fontsize=11)
                ax.set_ylabel(y_label, fontsize=11)

                # Rotate x labels if too many
                if len(x_data) > 6:
                    plt.xticks(rotation=45, ha='right')

            plt.tight_layout()

            # Convert to base64
            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            chart_base64 = base64.b64encode(buf.read()).decode('utf-8')
            plt.close(fig)

            # Generate summary
            data_summary = self._generate_summary(x_data, y_data_dict, y_cols)

            return {
                "chart_base64": chart_base64,
                "chart_type": chart_type,
                "data_summary": data_summary,
            }

        except Exception as e:
            error_msg = f"Error generating chart -> {str(e)}"
            logger.error(error_msg)
            plt.close('all')
            return {"error": error_msg, "chart_base64": "", "chart_type": chart_type}

    def _detect_axes(self, columns: List[str], rows: List[Dict]) -> tuple:
        """Auto-detect which columns to use for x and y axes."""
        x_col = columns[0]
        y_cols = []

        for col in columns[1:]:
            # Check if column is numeric
            sample = rows[0][col] if isinstance(rows[0], dict) else rows[0][columns.index(col)]
            try:
                float(sample)
                y_cols.append(col)
            except (ValueError, TypeError):
                continue

        if not y_cols and len(columns) > 1:
            y_cols = [columns[1]]

        return x_col, y_cols

    def _create_bar_chart(self, ax, x_data, y_data_dict, y_cols):
        """Create a bar chart."""
        x_str = [str(x) for x in x_data]
        if len(y_cols) == 1:
            colors = plt.cm.Set2(range(len(x_str)))
            ax.bar(x_str, list(y_data_dict.values())[0], color=colors)
        else:
            import numpy as np
            x_pos = np.arange(len(x_str))
            width = 0.8 / len(y_cols)
            for i, col in enumerate(y_cols):
                offset = (i - len(y_cols) / 2 + 0.5) * width
                ax.bar(x_pos + offset, y_data_dict[col], width, label=col)
            ax.set_xticks(x_pos)
            ax.set_xticklabels(x_str)
            ax.legend()

    def _create_line_chart(self, ax, x_data, y_data_dict, y_cols):
        """Create a line chart."""
        for col in y_cols:
            ax.plot(range(len(x_data)), y_data_dict[col], marker='o', label=col, linewidth=2)
        ax.set_xticks(range(len(x_data)))
        ax.set_xticklabels([str(x) for x in x_data])
        if len(y_cols) > 1:
            ax.legend()

    def _create_pie_chart(self, ax, labels, values):
        """Create a pie chart."""
        str_labels = [str(l) for l in labels]
        colors = plt.cm.Set2(range(len(str_labels)))
        ax.pie(values, labels=str_labels, autopct='%1.1f%%', colors=colors, startangle=90)
        ax.axis('equal')

    def _create_scatter_chart(self, ax, x_data, y_data_dict, y_cols):
        """Create a scatter plot."""
        try:
            x_numeric = [float(x) for x in x_data]
        except (ValueError, TypeError):
            x_numeric = list(range(len(x_data)))

        for col in y_cols:
            ax.scatter(x_numeric, y_data_dict[col], label=col, alpha=0.7, s=50)
        if len(y_cols) > 1:
            ax.legend()

    def _generate_summary(self, x_data, y_data_dict, y_cols) -> str:
        """Generate a brief text summary of the chart data."""
        parts = [f"Chart shows {len(x_data)} data points."]
        for col in y_cols:
            values = y_data_dict[col]
            parts.append(f"{col}: min={min(values):.2f}, max={max(values):.2f}, avg={sum(values)/len(values):.2f}")
        return " ".join(parts)
