"""
SQL Injection Prevention Guidelines

This module provides utilities to prevent SQL injection vulnerabilities.
All database queries MUST follow these guidelines.
"""
import logging
from sqlalchemy import text
from typing import Any, Dict

logger = logging.getLogger(__name__)


class SQLInjectionError(Exception):
    """Raised when potential SQL injection is detected."""
    pass


def validate_query_safety(query_string: str, params: Dict[str, Any]) -> bool:
    """
    Validate that a query uses parameterized syntax and doesn't contain
    dangerous patterns.
    
    Args:
        query_string: The SQL query string
        params: Dictionary of parameters
        
    Returns:
        True if query appears safe
        
    Raises:
        SQLInjectionError: If dangerous patterns detected
    """
    # Check for f-string interpolation markers
    if '{' in query_string or '}' in query_string:
        raise SQLInjectionError(
            "Query contains f-string interpolation markers. "
            "Use parameterized queries with :param_name syntax instead."
        )
    
    # Check for string concatenation patterns
    dangerous_patterns = [
        "' + ",
        '" + ',
        "' || ",
        '" || ',
    ]
    
    for pattern in dangerous_patterns:
        if pattern in query_string:
            raise SQLInjectionError(
                f"Query contains dangerous concatenation pattern: {pattern}. "
                "Use parameterized queries instead."
            )
    
    return True


def safe_text_query(query_string: str, params: Dict[str, Any] = None):
    """
    Create a safe SQLAlchemy text() query with validation.
    
    Usage:
        query = safe_text_query('''
            SELECT * FROM users WHERE email = :email
        ''', {'email': user_email})
        
        results = db.execute(query).fetchall()
    
    Args:
        query_string: SQL query with :param_name placeholders
        params: Dictionary of parameters (optional)
        
    Returns:
        SQLAlchemy text() object
        
    Raises:
        SQLInjectionError: If query contains dangerous patterns
    """
    params = params or {}
    
    # Validate query safety
    validate_query_safety(query_string, params)
    
    # Log query for audit (without sensitive data)
    logger.debug(f"Executing parameterized query with {len(params)} parameters")
    
    return text(query_string)


# Guidelines for developers:
"""
✅ SAFE - Use parameterized queries:
    query = text("SELECT * FROM users WHERE email = :email")
    db.execute(query, {"email": user_input})

✅ SAFE - Use SQLAlchemy ORM:
    db.query(User).filter(User.email == user_input).all()

❌ UNSAFE - Never use f-strings with user input:
    query = text(f"SELECT * FROM users WHERE email = '{user_input}'")

❌ UNSAFE - Never concatenate user input:
    query = text("SELECT * FROM users WHERE email = '" + user_input + "'")

❌ UNSAFE - Never use .format() with user input:
    query = text("SELECT * FROM users WHERE email = '{}'".format(user_input))

⚠️ CAUTION - f-strings are OK for static SQL structure (no user input):
    query = text(f"SELECT * FROM {table_name} WHERE id = :id")  # Only if table_name is hardcoded
    
    But prefer this instead:
    query = text("SELECT * FROM users WHERE id = :id")  # Explicit table name
"""
