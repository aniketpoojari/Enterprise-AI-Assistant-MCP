"""Natural language to SQL conversion service."""

from typing import Dict, Any

from utils.model_loader import ModelLoader
from utils.sql_utils import validate_sql, extract_sql_from_response
from models.database import DatabaseManager
from prompt_library.prompts import NL_TO_SQL_SYSTEM_PROMPT, NL_TO_SQL_USER_PROMPT
from utils.cost_tracker import CostTracker
from logger.logging import get_logger

logger = get_logger(__name__)


class NLToSQLService:
    """Converts natural language questions to SQL and executes them."""

    def __init__(self, model_provider: str = "groq"):
        try:
            self.model_loader = ModelLoader(model_provider)
            self.llm = self.model_loader.load_llm()
            self.db = DatabaseManager()
            self.cost_tracker = CostTracker()
            self.schema = self.db.get_schema_summary()
            logger.info("NLToSQLService initialized")

        except Exception as e:
            error_msg = f"Error in NLToSQLService Initialization -> {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

    def generate_sql(self, question: str) -> Dict[str, Any]:
        """Generate SQL from a natural language question."""
        try:
            system_prompt = NL_TO_SQL_SYSTEM_PROMPT.format(schema=self.schema)
            user_prompt = NL_TO_SQL_USER_PROMPT.format(question=question)

            from langchain_core.messages import SystemMessage, HumanMessage
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]

            response = self.llm.invoke(messages)
            cost_info = self.cost_tracker.track_call(response)

            sql = extract_sql_from_response(response.content)

            return {
                "sql": sql,
                "cost": cost_info,
                "raw_response": response.content,
            }

        except Exception as e:
            error_msg = f"Error generating SQL -> {str(e)}"
            logger.error(error_msg)
            return {"sql": "", "error": error_msg, "cost": {}}

    def execute(self, question: str, max_rows: int = 100) -> Dict[str, Any]:
        """Generate SQL, validate it, and execute it."""
        try:
            # Generate SQL
            gen_result = self.generate_sql(question)
            if gen_result.get("error"):
                return gen_result

            sql = gen_result["sql"]

            # Validate SQL
            is_valid, error_msg = validate_sql(sql)
            if not is_valid:
                logger.warning(f"SQL validation failed: {error_msg}")
                return {
                    "sql": sql,
                    "error": f"SQL validation failed: {error_msg}",
                    "cost": gen_result.get("cost", {}),
                    "columns": [],
                    "rows": [],
                    "row_count": 0,
                }

            # Execute query
            result = self.db.execute_query(sql, max_rows=max_rows)

            if result.get("error"):
                return {
                    "sql": sql,
                    "error": result["error"],
                    "cost": gen_result.get("cost", {}),
                    "columns": [],
                    "rows": [],
                    "row_count": 0,
                }

            return {
                "sql": sql,
                "columns": result["columns"],
                "rows": result["rows"],
                "row_count": result["row_count"],
                "execution_time_ms": result["execution_time_ms"],
                "truncated": result.get("truncated", False),
                "cost": gen_result.get("cost", {}),
            }

        except Exception as e:
            error_msg = f"Error in NLToSQLService.execute -> {str(e)}"
            logger.error(error_msg)
            return {"sql": "", "error": error_msg, "columns": [], "rows": [], "row_count": 0}
