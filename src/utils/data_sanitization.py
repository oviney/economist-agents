#!/usr/bin/env python3
"""
Data Sanitization Utility Functions

Provides secure data sanitization for various input types.
Enhanced with security improvements based on senior review feedback.
"""

import re
import logging
from pathlib import Path
from typing import Dict, Any, Union

# Configure logging for security events
logger = logging.getLogger(__name__)

# Configuration constants
MAX_INPUT_SIZE = 10 * 1024 * 1024  # 10MB max input size
MAX_EMAIL_LENGTH = 254  # RFC 5321 limit
MAX_PATH_LENGTH = 4096  # Typical filesystem limit

# Pre-compiled regex patterns for performance
HTML_TAG_PATTERN = re.compile(r'<[^>]*>')
EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')


def _validate_input_size(input_data: Union[str, None], max_size: int) -> bool:
    """Validate input size to prevent DoS attacks."""
    if input_data is None:
        return True
    if isinstance(input_data, str) and len(input_data) > max_size:
        logger.warning(f"Input size {len(input_data)} exceeds maximum {max_size}")
        return False
    return True


def sanitize_html(input_text: Union[str, None]) -> str:
    """
    Remove HTML tags from input text with enhanced security.

    Args:
        input_text: Text that may contain HTML tags

    Returns:
        Text with HTML tags removed

    Raises:
        ValueError: If input exceeds size limits
    """
    if input_text is None:
        return ""

    if not isinstance(input_text, str):
        return ""

    # Validate input size
    if not _validate_input_size(input_text, MAX_INPUT_SIZE):
        raise ValueError(f"Input size exceeds maximum allowed ({MAX_INPUT_SIZE} bytes)")

    # Remove HTML tags using pre-compiled regex
    clean_text = HTML_TAG_PATTERN.sub('', input_text)

    # Log security event if HTML tags were found
    if clean_text != input_text:
        logger.info("HTML tags removed from input")

    return clean_text


def sanitize_sql(input_text: str) -> str:
    """
    Sanitize SQL injection attempts with proper escaping.

    Args:
        input_text: Text that may contain SQL injection patterns

    Returns:
        Sanitized text with SQL patterns neutralized

    Raises:
        ValueError: If input exceeds size limits
    """
    if not isinstance(input_text, str):
        return ""

    # Validate input size
    if not _validate_input_size(input_text, MAX_INPUT_SIZE):
        raise ValueError(f"Input size exceeds maximum allowed ({MAX_INPUT_SIZE} bytes)")

    # SQL injection patterns to detect
    sql_patterns = [
        r"('|(\\')|(;)|(\\';)|(--)|(--)|(\\--))",
        r"((\%27)|(\\')|(;)|(\\%27)|(\\%3B))",
        r"(union)|(select)|(insert)|(delete)|(update)|(drop)|(create)|(alter)",
        r"(script)|(javascript)|(vbscript)|(iframe)|(object)|(embed)"
    ]

    original_text = input_text

    # Escape dangerous characters
    sanitized = input_text.replace("'", "''")  # Escape single quotes
    sanitized = sanitized.replace(";", "\\;")   # Escape semicolons
    sanitized = sanitized.replace("--", "\\--") # Escape SQL comments

    # Log security event if SQL patterns detected
    for pattern in sql_patterns:
        if re.search(pattern, input_text, re.IGNORECASE):
            logger.warning(f"Potential SQL injection detected: {pattern}")
            break

    return sanitized if sanitized != original_text else input_text


def validate_email(email: Union[str, None]) -> bool:
    """
    Validate email format with enhanced security checks.

    Args:
        email: Email address to validate

    Returns:
        True if email format is valid, False otherwise
    """
    if email is None or not isinstance(email, str):
        return False

    if not email or len(email) > MAX_EMAIL_LENGTH:
        return False

    # Enhanced email validation with pre-compiled regex
    if not EMAIL_PATTERN.match(email):
        return False

    # Additional security checks
    # Prevent emails with suspicious patterns
    suspicious_patterns = [
        r'[<>"]',  # HTML/script injection
        r'javascript:',  # JavaScript injection
        r'%[0-9a-fA-F]{2}',  # URL encoding
    ]

    for pattern in suspicious_patterns:
        if re.search(pattern, email, re.IGNORECASE):
            logger.warning("Suspicious email pattern detected")
            return False

    return True


def sanitize_path(file_path: Union[str, None]) -> str:
    """
    Sanitize file paths to prevent directory traversal with enhanced security.

    Args:
        file_path: File path that may contain traversal patterns

    Returns:
        Sanitized path with traversal patterns removed

    Raises:
        ValueError: If path exceeds length limits
    """
    if file_path is None or not isinstance(file_path, str):
        return ""

    if not file_path.strip():  # Handle empty or whitespace-only strings
        return ""

    if len(file_path) > MAX_PATH_LENGTH:
        raise ValueError(f"Path length exceeds maximum allowed ({MAX_PATH_LENGTH} characters)")

    try:
        # Use pathlib for robust path handling
        path = Path(file_path)

        # Convert to absolute path and resolve '..' components
        # Then get relative path to prevent traversal
        resolved = path.resolve()

        # Convert back to string and remove leading slashes
        clean_path = str(resolved).lstrip('/')

        # Additional security: remove common traversal patterns
        traversal_patterns = [
            '../', '..\\', './',
            '%2e%2e%2f', '%2e%2e%5c',  # URL encoded
            '%252e%252e%252f',  # Double URL encoded
        ]

        for pattern in traversal_patterns:
            if pattern.lower() in file_path.lower():
                logger.warning(f"Path traversal attempt detected: {pattern}")

        # Remove any remaining traversal components
        clean_path = clean_path.replace('../', '').replace('..\\', '')
        clean_path = re.sub(r'/+', '/', clean_path)
        clean_path = clean_path.lstrip('/')

        return clean_path

    except (OSError, ValueError) as e:
        logger.error(f"Path sanitization error: {e}")
        return ""


def sanitize_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Comprehensive data sanitization for dictionary input.

    Args:
        data: Dictionary containing data to sanitize

    Returns:
        Dictionary with sanitized values

    Raises:
        ValueError: If input is None or not a dictionary
    """
    if data is None:
        raise ValueError("Input data cannot be None")

    if not isinstance(data, dict):
        raise ValueError("Input must be a dictionary")

    if not data:  # Empty dict
        return {}

    sanitized = {}

    for key, value in data.items():
        if isinstance(value, str):
            # Apply different sanitization based on key name
            if 'html' in key.lower() or 'content' in key.lower():
                sanitized[key] = sanitize_html(value)
            elif 'email' in key.lower():
                sanitized[key] = value  # Keep valid emails as-is
            elif 'path' in key.lower() or 'file' in key.lower():
                sanitized[key] = sanitize_path(value)
            elif 'sql' in key.lower() or 'query' in key.lower():
                sanitized[key] = sanitize_sql(value)
            else:
                sanitized[key] = value  # Keep other text as-is
        else:
            sanitized[key] = value  # Keep non-string values as-is

    return sanitized


# Utility function for testing
def run_sanitization_tests():
    """Run basic sanitization tests to verify functionality."""
    # Test HTML sanitization
    html_test = "<p>Hello <script>alert('xss')</script> World</p>"
    print(f"HTML Input: {html_test}")
    print(f"HTML Output: {sanitize_html(html_test)}")

    # Test email validation
    emails = ["user@example.com", "invalid-email", "test@domain.co.uk"]
    for email in emails:
        print(f"Email {email}: {'Valid' if validate_email(email) else 'Invalid'}")

    # Test path sanitization
    paths = ["../../../etc/passwd", "uploads/image.jpg", "//double/slash"]
    for path in paths:
        print(f"Path '{path}' -> '{sanitize_path(path)}'")


if __name__ == "__main__":
    run_sanitization_tests()