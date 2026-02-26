"""Run the full evaluation suite for the Enterprise AI Assistant."""

import json
import sys
from datetime import datetime
from pathlib import Path

from evaluation.eval_agent_decisions import AgentDecisionEvaluator
from evaluation.eval_guardrails import GuardrailEvaluator
from evaluation.eval_sql_accuracy import SQLAccuracyEvaluator
from logger.logging import get_logger, setup_logging

setup_logging(log_level="INFO")
logger = get_logger(__name__)


def run_full_evaluation(max_queries: int = None):
    """Run all evaluation suites and produce a summary report."""
    results = {}
    start_time = datetime.now()

    logger.info("=" * 60)
    logger.info("ENTERPRISE AI ASSISTANT - EVALUATION SUITE")
    logger.info("=" * 60)

    # 1. SQL Accuracy
    logger.info("\n--- SQL Accuracy Evaluation ---")
    try:
        sql_eval = SQLAccuracyEvaluator()
        sql_results = sql_eval.evaluate(max_queries=max_queries)
        results["sql_accuracy"] = sql_results
        logger.info(
            f"SQL Accuracy: {sql_results['accuracy']:.1%} ({sql_results['passed']}/{sql_results['total']})"
        )
    except Exception as e:
        logger.error(f"SQL evaluation failed: {e}")
        results["sql_accuracy"] = {"error": str(e)}

    # 2. Guardrail Effectiveness
    logger.info("\n--- Guardrail Evaluation ---")
    try:
        guard_eval = GuardrailEvaluator()
        guard_results = guard_eval.evaluate()
        results["guardrails"] = guard_results
        logger.info(
            f"Input Detection Rate: {guard_results['input_detection_rate']:.1%}"
        )
        logger.info(
            f"Output Detection Rate: {guard_results['output_detection_rate']:.1%}"
        )
    except Exception as e:
        logger.error(f"Guardrail evaluation failed: {e}")
        results["guardrails"] = {"error": str(e)}

    # 3. Agent Decisions
    logger.info("\n--- Agent Decision Evaluation ---")
    try:
        agent_eval = AgentDecisionEvaluator()
        agent_results = agent_eval.evaluate()
        results["agent_decisions"] = agent_results
        logger.info(f"Routing Accuracy: {agent_results['routing_accuracy']:.1%}")
    except Exception as e:
        logger.error(f"Agent decision evaluation failed: {e}")
        results["agent_decisions"] = {"error": str(e)}

    # Summary
    elapsed = (datetime.now() - start_time).total_seconds()
    results["metadata"] = {
        "timestamp": start_time.isoformat(),
        "duration_seconds": round(elapsed, 1),
        "max_queries": max_queries,
    }

    logger.info("\n" + "=" * 60)
    logger.info("EVALUATION COMPLETE")
    logger.info(f"Duration: {elapsed:.1f}s")
    logger.info("=" * 60)

    # Save results
    output_path = Path("evaluation/results.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    logger.info(f"Results saved to {output_path}")

    return results


if __name__ == "__main__":
    import os

    max_q = int(os.getenv("EVAL_MAX_QUERIES", "0")) or None
    run_full_evaluation(max_queries=max_q)
