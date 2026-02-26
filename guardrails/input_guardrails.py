"""Input guardrails - validate and sanitize user input before processing."""

import re
import yaml
from pathlib import Path
from typing import Dict, Any, List, Tuple

from guardrails.patterns import INJECTION_PATTERNS, PII_PATTERNS, OFF_TOPIC_PATTERNS
from logger.logging import get_logger

logger = get_logger(__name__)


class InputGuardrails:
    """Validates user input for safety before passing to the agent."""

    def __init__(self, config_path: str = "config/guardrails_config.yaml"):
        try:
            self.config = self._load_config(config_path)
            self.input_config = self.config.get("input_guardrails", {})
            logger.info("InputGuardrails initialized")

        except Exception as e:
            error_msg = f"Error in InputGuardrails Initialization -> {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

    def _load_config(self, config_path: str) -> Dict:
        """Load guardrails configuration."""
        path = Path(config_path)
        if path.exists():
            with open(path, 'r') as f:
                return yaml.safe_load(f) or {}
        return {}

    def check_all(self, user_input: str) -> List[Dict[str, Any]]:
        """Run all input guardrails and return results.

        Returns:
            List of guardrail check results, each with:
            - guardrail_name: str
            - status: 'passed' | 'blocked' | 'warning'
            - message: str
            - confidence: float (0-1)
        """
        results = []

        # 1. Prompt injection detection
        if self.input_config.get("injection_detection", {}).get("enabled", True):
            results.append(self.check_injection(user_input))

        # 2. PII filtering
        if self.input_config.get("pii_filter", {}).get("enabled", True):
            results.append(self.check_pii(user_input))

        # 3. Query validation
        if self.input_config.get("query_validation", {}).get("enabled", True):
            results.append(self.check_query_validity(user_input))

        return results

    def is_blocked(self, results: List[Dict[str, Any]]) -> bool:
        """Check if any guardrail blocked the input."""
        return any(r["status"] == "blocked" for r in results)

    def get_block_reason(self, results: List[Dict[str, Any]]) -> str:
        """Get the reason for blocking."""
        blocked = [r for r in results if r["status"] == "blocked"]
        if blocked:
            return blocked[0]["message"]
        return ""

    def check_injection(self, text: str) -> Dict[str, Any]:
        """Check for prompt injection attempts using regex patterns."""
        for pattern in INJECTION_PATTERNS:
            match = pattern.search(text)
            if match:
                logger.warning(f"Prompt injection detected: {match.group()[:50]}")
                return {
                    "guardrail_name": "injection_detection",
                    "status": "blocked",
                    "message": "Potential prompt injection detected. Please rephrase your question about the business data.",
                    "confidence": 0.9,
                }

        return {
            "guardrail_name": "injection_detection",
            "status": "passed",
            "message": "No injection detected",
            "confidence": 1.0,
        }

    def check_pii(self, text: str) -> Dict[str, Any]:
        """Check for PII in the user input."""
        detected_pii = []

        for pii_type, pattern in PII_PATTERNS.items():
            if pattern.search(text):
                detected_pii.append(pii_type)

        if detected_pii:
            logger.warning(f"PII detected in input: {detected_pii}")
            return {
                "guardrail_name": "pii_filter",
                "status": "warning",
                "message": f"Personal information detected ({', '.join(detected_pii)}). Please avoid including sensitive data in queries.",
                "confidence": 0.85,
            }

        return {
            "guardrail_name": "pii_filter",
            "status": "passed",
            "message": "No PII detected",
            "confidence": 1.0,
        }

    def check_query_validity(self, text: str) -> Dict[str, Any]:
        """Check if the query is relevant and within bounds."""
        # Check max length
        max_len = self.input_config.get("query_validation", {}).get("max_query_length", 1000)
        if len(text) > max_len:
            return {
                "guardrail_name": "query_validation",
                "status": "blocked",
                "message": f"Query exceeds maximum length of {max_len} characters.",
                "confidence": 1.0,
            }

        # Check for off-topic patterns
        for pattern in OFF_TOPIC_PATTERNS:
            if pattern.search(text):
                return {
                    "guardrail_name": "query_validation",
                    "status": "blocked",
                    "message": "This question appears to be off-topic. I can help with e-commerce business analytics questions.",
                    "confidence": 0.75,
                }

        return {
            "guardrail_name": "query_validation",
            "status": "passed",
            "message": "Query is valid",
            "confidence": 1.0,
        }
