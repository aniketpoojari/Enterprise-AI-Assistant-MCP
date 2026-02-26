"""LangGraph agent workflow for the Enterprise AI Assistant."""

from typing import Any, Dict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from agent.state import AgentState
from logger.logging import get_logger
from prompt_library.prompts import (
    AGENT_SYSTEM_PROMPT,
    GENERAL_RESPONSE_PROMPT,
    ROUTER_PROMPT,
)
from services.guardrail_service import GuardrailService
from tools.chart_tool import generate_chart
from tools.report_tool import generate_report
from tools.sql_query_tool import query_database
from utils.cost_tracker import CostTracker
from utils.model_loader import ModelLoader

logger = get_logger(__name__)


class EnterpriseAssistantWorkflow:
    """LangGraph workflow for the Enterprise AI Assistant."""

    def __init__(self, model_provider: str = "groq"):
        try:
            self.model_loader = ModelLoader(model_provider)
            self.llm = self.model_loader.load_llm()
            self.cost_tracker = CostTracker()
            self.guardrail_service = GuardrailService()

            # All tools available to the agent
            self.tools = [query_database, generate_chart, generate_report]
            self.llm_with_tools = self.llm.bind_tools(self.tools)

            self.graph = None
            logger.info("EnterpriseAssistantWorkflow initialized")

        except Exception as e:
            error_msg = (
                f"Error in EnterpriseAssistantWorkflow Initialization -> {str(e)}"
            )
            logger.error(error_msg)
            raise Exception(error_msg)

    def build_graph(self):
        """Build the LangGraph state graph."""
        try:
            graph = StateGraph(AgentState)

            # Add nodes
            graph.add_node("router", self.router_node)
            graph.add_node("guardrail_check", self.guardrail_node)
            graph.add_node("agent", self.agent_node)
            graph.add_node("tools", ToolNode(self.tools))
            graph.add_node("output_guard", self.output_guardrail_node)
            graph.add_node("general_response", self.general_response_node)

            # Define edges
            graph.add_edge(START, "router")
            graph.add_conditional_edges(
                "router",
                self._route_by_intent,
                {
                    "general": "general_response",
                    "data_query": "guardrail_check",
                },
            )
            graph.add_conditional_edges(
                "guardrail_check",
                self._check_guardrail_result,
                {
                    "allowed": "agent",
                    "blocked": END,
                },
            )
            graph.add_conditional_edges(
                "agent",
                tools_condition,
            )
            graph.add_edge("tools", "output_guard")
            graph.add_conditional_edges(
                "output_guard",
                self._check_output_guardrail,
                {
                    "allowed": "agent",
                    "blocked": END,
                },
            )
            graph.add_edge("general_response", END)

            self.graph = graph.compile()
            logger.info("Agent graph built successfully")

        except Exception as e:
            error_msg = f"Error building graph -> {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

    def router_node(self, state: AgentState) -> Dict[str, Any]:
        """Classify user intent."""
        try:
            last_message = state["messages"][-1]
            query = (
                last_message.content
                if hasattr(last_message, "content")
                else str(last_message)
            )

            prompt = ROUTER_PROMPT.format(query=query)
            response = self.llm.invoke(prompt)

            intent = response.content.strip().lower()
            logger.info(f"Router classified intent: {intent}")

            return {
                "intent": intent,
                "cost_info": [self.cost_tracker.track_call(response)],
            }

        except Exception as e:
            logger.error(f"Error in router -> {str(e)}")
            return {"intent": "general", "cost_info": []}

    def guardrail_node(self, state: AgentState) -> Dict[str, Any]:
        """Run input guardrails."""
        try:
            last_message = state["messages"][-1]
            query = (
                last_message.content
                if hasattr(last_message, "content")
                else str(last_message)
            )

            result = self.guardrail_service.check_input(query)

            if not result["allowed"]:
                return {
                    "guardrail_results": result["results"],
                    "messages": [
                        AIMessage(
                            content=f"I can't process that request. {result['block_reason']}"
                        )
                    ],
                }

            return {"guardrail_results": result["results"]}

        except Exception as e:
            logger.error(f"Error in guardrail node -> {str(e)}")
            return {"guardrail_results": []}

    def agent_node(self, state: AgentState) -> Dict[str, Any]:
        """Main agent node - decides which tools to use."""
        try:
            system_msg = SystemMessage(content=AGENT_SYSTEM_PROMPT)
            messages = [system_msg] + state["messages"]

            response = self.llm_with_tools.invoke(messages)
            cost = self.cost_tracker.track_call(response)

            existing_cost = state.get("cost_info", [])
            existing_cost.append(cost)

            return {
                "messages": [response],
                "cost_info": existing_cost,
            }

        except Exception as e:
            logger.error(f"Error in agent node -> {str(e)}")
            return {
                "messages": [
                    AIMessage(
                        content=f"I encountered an error processing your request: {str(e)}"
                    )
                ],
            }

    def output_guardrail_node(self, state: AgentState) -> Dict[str, Any]:
        """Run output guardrails on tool results."""
        try:
            # Find the last tool message
            for msg in reversed(state["messages"]):
                if hasattr(msg, "content") and isinstance(msg.content, str):
                    # Check if it contains SQL
                    import json

                    try:
                        data = json.loads(msg.content)
                        sql = data.get("sql", "")
                        rows = data.get("rows", [])
                        columns = data.get("columns", [])

                        if sql:
                            result = self.guardrail_service.check_output(
                                sql=sql, rows=rows, columns=columns
                            )

                            if not result["allowed"]:
                                return {
                                    "messages": [
                                        AIMessage(
                                            content="The generated query was blocked by safety checks. Please rephrase your question."
                                        )
                                    ],
                                    "guardrail_results": state.get(
                                        "guardrail_results", []
                                    )
                                    + result["results"],
                                }

                            # Replace rows with masked version
                            if (
                                result.get("masked_rows")
                                and result["masked_rows"] != rows
                            ):
                                data["rows"] = result["masked_rows"]
                                from langchain_core.messages import ToolMessage

                                # Update with masked data
                                return {
                                    "guardrail_results": state.get(
                                        "guardrail_results", []
                                    )
                                    + result["results"],
                                }
                    except (json.JSONDecodeError, TypeError):
                        pass

            return {"guardrail_results": state.get("guardrail_results", [])}

        except Exception as e:
            logger.error(f"Error in output guardrail node -> {str(e)}")
            return {}

    def general_response_node(self, state: AgentState) -> Dict[str, Any]:
        """Handle general/off-topic queries."""
        try:
            last_message = state["messages"][-1]
            query = (
                last_message.content
                if hasattr(last_message, "content")
                else str(last_message)
            )

            prompt = GENERAL_RESPONSE_PROMPT.format(query=query)
            response = self.llm.invoke(prompt)
            cost = self.cost_tracker.track_call(response)

            return {
                "messages": [AIMessage(content=response.content)],
                "cost_info": state.get("cost_info", []) + [cost],
            }

        except Exception as e:
            logger.error(f"Error in general response -> {str(e)}")
            return {
                "messages": [
                    AIMessage(
                        content="Hello! I'm the Enterprise AI Assistant. I can help you analyze e-commerce data. Try asking about products, orders, customers, or revenue!"
                    )
                ],
            }

    # --- Edge condition functions ---

    def _route_by_intent(self, state: AgentState) -> str:
        """Route based on classified intent."""
        intent = state.get("intent", "general")
        if intent in ("sql_query", "visualization", "report"):
            return "data_query"
        return "general"

    def _check_guardrail_result(self, state: AgentState) -> str:
        """Check if input guardrails allowed the query."""
        results = state.get("guardrail_results", [])
        if any(r.get("status") == "blocked" for r in results):
            return "blocked"
        return "allowed"

    def _check_output_guardrail(self, state: AgentState) -> str:
        """Check if output guardrails blocked the response."""
        results = state.get("guardrail_results", [])
        # Check only the most recent results
        if results and results[-1].get("status") == "blocked":
            return "blocked"
        return "allowed"

    def invoke(self, query: str, conversation_id: str = None) -> Dict[str, Any]:
        """Run the agent workflow on a user query."""
        if self.graph is None:
            self.build_graph()

        try:
            initial_state = {
                "messages": [HumanMessage(content=query)],
                "intent": "",
                "sql_result": {},
                "chart_result": {},
                "report_result": {},
                "guardrail_results": [],
                "tools_used": [],
                "cost_info": [],
            }

            result = self.graph.invoke(initial_state)

            # Extract final response
            messages = result.get("messages", [])
            final_response = ""
            for msg in reversed(messages):
                if isinstance(msg, AIMessage) and msg.content and not msg.tool_calls:
                    final_response = msg.content
                    break

            # Aggregate costs
            total_cost = {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "estimated_cost_usd": 0,
            }
            for c in result.get("cost_info", []):
                total_cost["prompt_tokens"] += c.get("prompt_tokens", 0)
                total_cost["completion_tokens"] += c.get("completion_tokens", 0)
                total_cost["total_tokens"] += c.get("total_tokens", 0)
                total_cost["estimated_cost_usd"] += c.get("estimated_cost_usd", 0)

            return {
                "response": final_response,
                "intent": result.get("intent", ""),
                "guardrail_results": result.get("guardrail_results", []),
                "cost": total_cost,
                "messages": messages,
            }

        except Exception as e:
            error_msg = f"Error in workflow invoke -> {str(e)}"
            logger.error(error_msg)
            return {
                "response": f"I encountered an error: {str(e)}",
                "intent": "error",
                "guardrail_results": [],
                "cost": {},
                "messages": [],
            }
