"""Agent decision quality evaluation - tests routing and tool selection."""

import time
from typing import Any, Dict, List

from logger.logging import get_logger
from prompt_library.prompts import ROUTER_PROMPT
from utils.model_loader import ModelLoader

logger = get_logger(__name__)

# Delay between API calls to avoid Groq free-tier rate limits (30 req/min)
API_CALL_DELAY = 2.5

# Test cases for routing accuracy
ROUTING_TESTS = [
    {
        "query": "What are the top 10 products by revenue?",
        "expected_intent": "sql_query",
    },
    {"query": "Show me a chart of monthly sales", "expected_intent": "visualization"},
    {"query": "Generate a report on customer segments", "expected_intent": "report"},
    {"query": "Hello, what can you do?", "expected_intent": "general"},
    {"query": "How many orders were placed last week?", "expected_intent": "sql_query"},
    {"query": "Plot revenue by category", "expected_intent": "visualization"},
    {
        "query": "Write an executive summary of Q4 performance",
        "expected_intent": "report",
    },
    {"query": "Hi there!", "expected_intent": "general"},
    {
        "query": "Which customers have the highest lifetime value?",
        "expected_intent": "sql_query",
    },
    {
        "query": "Visualize the order status distribution",
        "expected_intent": "visualization",
    },
    {"query": "What is the average order value?", "expected_intent": "sql_query"},
    {
        "query": "Give me an analysis of product performance",
        "expected_intent": "report",
    },
    {"query": "What can you help me with?", "expected_intent": "general"},
    {"query": "Show products with rating above 4", "expected_intent": "sql_query"},
    {
        "query": "Create a bar chart of revenue by payment method",
        "expected_intent": "visualization",
    },
]


class AgentDecisionEvaluator:
    """Evaluates agent routing and decision quality."""

    def __init__(self, model_provider: str = "groq"):
        self.model_loader = ModelLoader(model_provider)
        self.llm = self.model_loader.load_llm()

    def evaluate(self) -> Dict[str, Any]:
        """Run agent decision evaluation."""
        correct = 0
        total = len(ROUTING_TESTS)
        details = []

        for i, test in enumerate(ROUTING_TESTS):
            # Rate-limit delay between calls
            if i > 0:
                time.sleep(API_CALL_DELAY)

            try:
                logger.info(f"[{i+1}/{total}] Routing: {test['query'][:60]}...")
                prompt = ROUTER_PROMPT.format(query=test["query"])
                response = self.llm.invoke(prompt)
                actual_intent = response.content.strip().lower()

                # Normalize intent names
                expected = test["expected_intent"]
                is_correct = actual_intent == expected

                if is_correct:
                    correct += 1

                details.append(
                    {
                        "query": test["query"],
                        "expected": expected,
                        "actual": actual_intent,
                        "correct": is_correct,
                    }
                )

            except Exception as e:
                details.append(
                    {
                        "query": test["query"],
                        "expected": test["expected_intent"],
                        "actual": "error",
                        "correct": False,
                        "error": str(e),
                    }
                )

        return {
            "routing_accuracy": correct / total if total > 0 else 0,
            "correct": correct,
            "total": total,
            "details": details,
        }
