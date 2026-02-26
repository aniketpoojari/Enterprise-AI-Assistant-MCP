"""SQL accuracy evaluation - tests NL-to-SQL generation quality."""

import json
import time
from pathlib import Path
from typing import Any, Dict, List

from logger.logging import get_logger
from services.nl_to_sql_service import NLToSQLService

logger = get_logger(__name__)

# Delay between API calls to avoid Groq free-tier rate limits (30 req/min)
API_CALL_DELAY = 5


class SQLAccuracyEvaluator:
    """Evaluates SQL generation accuracy against gold-standard test queries."""

    def __init__(self):
        self.nl_to_sql = NLToSQLService()
        self.test_queries = self._load_test_queries()

    def _load_test_queries(self) -> List[Dict]:
        """Load test queries from JSON file."""
        path = Path(__file__).parent / "test_queries.json"
        with open(path, "r") as f:
            return json.load(f)

    def evaluate(self, max_queries: int = None) -> Dict[str, Any]:
        """Run SQL accuracy evaluation.

        Checks:
        1. SQL generation succeeds (no errors)
        2. Generated SQL contains expected keywords
        3. SQL executes without errors

        Returns:
            Dict with accuracy, passed, failed, total, details
        """
        queries = self.test_queries[:max_queries] if max_queries else self.test_queries
        results = []
        passed = 0
        failed = 0

        for i, test in enumerate(queries):
            question = test["question"]
            expected_contains = test["expected_sql_contains"]

            # Rate-limit delay between calls
            if i > 0:
                time.sleep(API_CALL_DELAY)

            try:
                logger.info(f"[{i+1}/{len(queries)}] Evaluating: {question[:60]}...")
                result = self.nl_to_sql.execute(question)

                sql = result.get("sql", "")
                error = result.get("error", "")
                has_rows = result.get("row_count", 0) > 0 or not error

                # Check if SQL contains expected keywords
                sql_upper = sql.upper()
                missing_keywords = [
                    kw for kw in expected_contains if kw.upper() not in sql_upper
                ]

                success = not error and sql and len(missing_keywords) == 0

                if success:
                    passed += 1
                else:
                    failed += 1

                results.append(
                    {
                        "id": test["id"],
                        "question": question,
                        "difficulty": test.get("difficulty", ""),
                        "generated_sql": sql,
                        "error": error,
                        "success": success,
                        "missing_keywords": missing_keywords,
                        "row_count": result.get("row_count", 0),
                    }
                )

            except Exception as e:
                failed += 1
                results.append(
                    {
                        "id": test["id"],
                        "question": question,
                        "success": False,
                        "error": str(e),
                    }
                )

        total = len(queries)
        return {
            "accuracy": passed / total if total > 0 else 0,
            "passed": passed,
            "failed": failed,
            "total": total,
            "details": results,
        }
