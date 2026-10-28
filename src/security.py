import re
from typing import Tuple, Optional

# Forbidden destructive or administrative keywords
FORBIDDEN_KEYWORDS = [
    r"\bDROP\b",
    r"\bDELETE\b",
    r"\bUPDATE\b",
    r"\bINSERT\b",
    r"\bALTER\b",
    r"\bTRUNCATE\b",
    r"\bREPLACE\b",
    r"\bCREATE\b",
    r"\bATTACH\b",
    r"\bDETACH\b",
    r"\bPRAGMA\b",
    r"\bVACUUM\b",
    r"\bREINDEX\b",
    r"\bGRANT\b",
    r"\bREVOKE\b",
    r"\bEXEC\b",
    r"\bEXECUTE\b",
]

ALLOWED_TABLES = {"sales", "v_monthly_sales"}

class SQLSecurityError(ValueError):
    """Raised when a SQL query fails security or safety validation."""
    pass

class SQLValidator:
    @staticmethod
    def sanitize_and_validate(sql: str) -> Tuple[bool, str, Optional[str]]:
        """
        Validates the SQL query against injection, destructive keywords, and schema rules.
        Returns: (is_valid, sanitized_sql, error_message)
        """
        if not sql or not sql.strip():
            return False, "", "Empty SQL query provided."

        # Strip markdown code blocks if LLM enclosed it
        cleaned = sql.strip()
        cleaned = re.sub(r"^```(sql)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

        # Remove single trailing semicolon if present
        if cleaned.endswith(";"):
            cleaned = cleaned[:-1].strip()

        # Reject query stacking (multiple statements separated by semicolons)
        if ";" in cleaned:
            return False, "", "Security violation: Multiple statements / query chaining (';') is strictly prohibited."

        # Reject SQL comments that could hide injection logic
        if "--" in cleaned or "/*" in cleaned:
            return False, "", "Security violation: SQL comments ('--', '/*') are not allowed in generated queries."

        # Ensure query begins with SELECT or WITH
        first_word_match = re.match(r"^\s*([a-zA-Z]+)", cleaned)
        if not first_word_match:
            return False, "", "Invalid SQL query: No leading command keyword found."

        first_word = first_word_match.group(1).upper()
        if first_word not in ("SELECT", "WITH"):
            return False, "", f"Security violation: Only read-only 'SELECT' queries are allowed. Attempted: '{first_word}'."

        # Check for any forbidden destructive keywords anywhere in query
        for pattern in FORBIDDEN_KEYWORDS:
            if re.search(pattern, cleaned, re.IGNORECASE):
                keyword = pattern.replace(r"\b", "")
                return False, "", f"Security violation: Destructive/Administrative keyword '{keyword}' is forbidden."

        # Verify query accesses allowed tables
        from_matches = re.findall(r"\bFROM\s+([a-zA-Z0-9_]+)", cleaned, re.IGNORECASE)
        join_matches = re.findall(r"\bJOIN\s+([a-zA-Z0-9_]+)", cleaned, re.IGNORECASE)
        all_referenced_tables = [t.lower() for t in from_matches + join_matches]

        for table in all_referenced_tables:
            if table not in ALLOWED_TABLES:
                return False, "", f"Security violation: Unauthorized table access '{table}'. Only {ALLOWED_TABLES} allowed."

        # Auto-append a safe LIMIT if no LIMIT clause is present to prevent denial-of-service / memory exhaustion
        if not re.search(r"\bLIMIT\s+\d+", cleaned, re.IGNORECASE):
            cleaned = f"{cleaned} LIMIT 100"

        return True, cleaned, None
