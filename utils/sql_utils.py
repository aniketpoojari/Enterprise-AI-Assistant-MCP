"""SQL validation and sanitization utilities."""

import re
from typing import List, Tuple

from logger.logging import get_logger

logger = get_logger(__name__)

# Dangerous SQL operations that should never appear in generated queries
BLOCKED_OPERATIONS = [
    "DROP",
    "DELETE",
    "UPDATE",
    "INSERT",
    "ALTER",
    "CREATE",
    "TRUNCATE",
    "EXEC",
    "EXECUTE",
    "GRANT",
    "REVOKE",
    "ATTACH",
    "DETACH",
    "VACUUM",
    "REINDEX",
    "PRAGMA",
]

# Allowed tables (must match schema.sql)
ALLOWED_TABLES = [
    "customers",
    "products",
    "orders",
    "order_items",
    "reviews",
    "inventory_log",
]


def validate_sql(sql: str, allowed_tables: List[str] = None) -> Tuple[bool, str]:
    """Validate a generated SQL query for safety.

    Returns:
        (is_valid, error_message)
    """
    if allowed_tables is None:
        allowed_tables = ALLOWED_TABLES

    sql_upper = sql.upper().strip()

    # Must start with SELECT or WITH (for CTEs)
    if not sql_upper.startswith("SELECT") and not sql_upper.startswith("WITH"):
        return False, "Only SELECT queries are allowed"

    # Check for blocked operations
    for op in BLOCKED_OPERATIONS:
        # Match as whole word to avoid false positives (e.g., "UPDATED_AT")
        pattern = rf"\b{op}\b"
        # Skip checking inside string literals by removing them first
        sql_no_strings = re.sub(r"'[^']*'", "", sql_upper)
        if re.search(pattern, sql_no_strings):
            return False, f"Blocked operation detected: {op}"

    # Check for multiple statements (SQL injection via semicolons)
    sql_no_strings = re.sub(r"'[^']*'", "", sql)
    if ";" in sql_no_strings.rstrip(";").rstrip():
        return False, "Multiple statements not allowed"

    # Check for comments (potential injection vector)
    if "--" in sql_no_strings or "/*" in sql_no_strings:
        return False, "SQL comments not allowed in generated queries"

    # Validate referenced tables
    # We parse FROM/JOIN clauses but must handle:
    #   - CTE names: WITH cte AS (...) SELECT ... FROM cte
    #   - Subquery aliases: FROM (SELECT ...) alias
    #   - EXTRACT syntax: EXTRACT(MONTH FROM col)
    #   - Function calls: FROM func(...)
    sql_clean = re.sub(r"'[^']*'", "", sql_upper)

    # Collect CTE names so we can exclude them
    cte_names = set()
    cte_pattern = r"\bWITH\s+(.*?)\bSELECT\b"
    cte_block = re.search(cte_pattern, sql_clean, re.DOTALL)
    if cte_block:
        for m in re.finditer(r"(\w+)\s+AS\s*\(", cte_block.group(1)):
            cte_names.add(m.group(1).lower())

    # Match table names after FROM/JOIN, but skip:
    #   - "(" after the name (subquery or function)
    #   - FROM preceded by EXTRACT/DISTINCT/etc. (not a table clause)
    table_pattern = r"\b(?:FROM|JOIN)\s+(\w+)(?!\s*\()"
    matches = re.findall(table_pattern, sql_clean)
    referenced_tables = set(t.lower() for t in matches)

    # Remove CTE names and common SQL keywords that aren't tables
    sql_keywords = {
        "select",
        "where",
        "and",
        "or",
        "not",
        "null",
        "as",
        "on",
        "in",
        "is",
        "by",
        "asc",
        "desc",
        "case",
        "when",
        "then",
        "else",
        "end",
        "between",
        "like",
        "having",
        "union",
        "all",
        "exists",
        "each",
        "lateral",
    }
    referenced_tables -= cte_names
    referenced_tables -= sql_keywords

    # Also remove any word captured from EXTRACT(... FROM column_name)
    extract_pattern = r"\bEXTRACT\s*\([^)]*\bFROM\s+(\w+)"
    for m in re.finditer(extract_pattern, sql_clean):
        referenced_tables.discard(m.group(1).lower())

    allowed_set = set(t.lower() for t in allowed_tables)
    invalid_tables = referenced_tables - allowed_set
    if invalid_tables:
        # Separate likely aliases (short, 1-3 chars) from truly unknown tables.
        # LLMs commonly alias "orders" as "o", "products" as "p", etc.
        likely_aliases = {t for t in invalid_tables if len(t) <= 3}
        truly_invalid = invalid_tables - likely_aliases

        if truly_invalid:
            return False, f"Referenced disallowed tables: {', '.join(truly_invalid)}"

        if likely_aliases:
            logger.info(f"SQL uses table aliases: {likely_aliases} (allowed)")

    return True, ""


def sanitize_sql(sql: str) -> str:
    """Clean up SQL for display/execution."""
    # Remove leading/trailing whitespace and semicolons
    sql = sql.strip().rstrip(";").strip()

    # Remove markdown code blocks if present
    if sql.startswith("```"):
        lines = sql.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        sql = "\n".join(lines).strip()

    return sql


def extract_sql_from_response(text: str) -> str:
    """Extract SQL query from an LLM response that may contain markdown or explanations."""
    # Try to find SQL in code blocks
    code_block_pattern = r"```(?:sql)?\s*\n?(.*?)\n?```"
    matches = re.findall(code_block_pattern, text, re.DOTALL | re.IGNORECASE)
    if matches:
        return sanitize_sql(matches[0])

    # Look for SELECT statement in the text
    select_pattern = r"((?:WITH\s+.*?\s+AS\s*\(.*?\)\s*)?SELECT\s+.*?)(?:\n\n|\Z)"
    matches = re.findall(select_pattern, text, re.DOTALL | re.IGNORECASE)
    if matches:
        return sanitize_sql(matches[0])

    # Fallback: return the whole text sanitized
    return sanitize_sql(text)
