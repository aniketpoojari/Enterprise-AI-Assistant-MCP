"""Token counting and cost estimation for the Enterprise AI Assistant."""

import json
import uuid
import time
from typing import Any, Dict, Optional, Callable
from functools import wraps

from utils.config_loader import ConfigLoader
from logger.logging import get_logger

logger = get_logger(__name__)


class CostTracker:
    """Tracks token usage and estimates costs for LLM calls."""

    def __init__(self):
        try:
            self.config = ConfigLoader()
            self.cost_per_1k_input = float(self.config.get("cost.groq_cost_per_1k_input_tokens", 0.00006))
            self.cost_per_1k_output = float(self.config.get("cost.groq_cost_per_1k_output_tokens", 0.00006))
            logger.info("CostTracker initialized")

        except Exception as e:
            error_msg = f"Error in CostTracker Initialization -> {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Estimate cost in USD for given token counts."""
        input_cost = (prompt_tokens / 1000) * self.cost_per_1k_input
        output_cost = (completion_tokens / 1000) * self.cost_per_1k_output
        return round(input_cost + output_cost, 8)

    def extract_usage(self, llm_response: Any) -> Dict[str, int]:
        """Extract token usage from an LLM response."""
        try:
            usage = {}

            # LangChain response with response_metadata
            if hasattr(llm_response, 'response_metadata'):
                metadata = llm_response.response_metadata
                token_usage = metadata.get('token_usage', {})
                usage = {
                    "prompt_tokens": token_usage.get('prompt_tokens', 0),
                    "completion_tokens": token_usage.get('completion_tokens', 0),
                    "total_tokens": token_usage.get('total_tokens', 0),
                }

            # Usage info directly
            elif hasattr(llm_response, 'usage_metadata'):
                um = llm_response.usage_metadata
                usage = {
                    "prompt_tokens": getattr(um, 'input_tokens', 0),
                    "completion_tokens": getattr(um, 'output_tokens', 0),
                    "total_tokens": getattr(um, 'total_tokens', 0),
                }

            # Ensure total is calculated
            if not usage.get("total_tokens"):
                usage["total_tokens"] = usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)

            return usage

        except Exception as e:
            logger.error(f"Error extracting usage -> {str(e)}")
            return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    def track_call(self, llm_response: Any, model_name: str = "llama-3.1-8b-instant") -> Dict[str, Any]:
        """Track a single LLM call and return cost info."""
        usage = self.extract_usage(llm_response)
        cost = self.estimate_cost(usage["prompt_tokens"], usage["completion_tokens"])

        return {
            "model_name": model_name,
            "prompt_tokens": usage["prompt_tokens"],
            "completion_tokens": usage["completion_tokens"],
            "total_tokens": usage["total_tokens"],
            "estimated_cost_usd": cost,
        }
