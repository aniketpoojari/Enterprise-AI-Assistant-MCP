"""Agent state definition for LangGraph workflow."""

from typing import List, Dict, Any
from langgraph.graph import MessagesState


class AgentState(MessagesState):
    """Custom state for the Enterprise AI Assistant agent."""
    intent: str
    sql_result: Dict[str, Any]
    chart_result: Dict[str, Any]
    report_result: Dict[str, Any]
    guardrail_results: List[Dict[str, Any]]
    tools_used: List[str]
    cost_info: List[Dict[str, Any]]
