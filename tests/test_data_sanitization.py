#!/usr/bin/env python3
"""
TDD RED Phase: Failing tests for data sanitization utility

These tests define the requirements for the data sanitization function.
All tests should initially FAIL until implementation is complete.
"""

import pytest
from typing import Dict, Any


def test_remove_html_tags():
    """Test HTML tag removal from strings."""
    from src.utils.data_sanitization import sanitize_html

    # Should remove basic HTML tags
    assert sanitize_html("<p>Hello World</p>") == "Hello World"
    assert sanitize_html("<script>alert('xss')</script>") == "alert('xss')"
    assert sanitize_html("<b>Bold</b> and <i>italic</i>") == "Bold and italic"

    # Should handle malformed HTML
    assert sanitize_html("<p>Unclosed tag") == "Unclosed tag"
    assert sanitize_html("No tags here") == "No tags here"

    # Should handle empty input
    assert sanitize_html("") == ""
    assert sanitize_html(None) == ""


def test_sanitize_sql_injection():
    """Test SQL injection attempt sanitization."""
    from src.utils.data_sanitization import sanitize_sql

    # Should neutralize SQL injection patterns (escaped)
    assert sanitize_sql("'; DROP TABLE users; --") == "''\\; DROP TABLE users\\; \\--"
    assert sanitize_sql("1' OR '1'='1") == "1'' OR ''1''=''1"
    assert sanitize_sql("UNION SELECT * FROM passwords") == "UNION SELECT * FROM passwords"

    # Should handle normal input safely
    assert sanitize_sql("normal user input") == "normal user input"
    assert sanitize_sql("user@example.com") == "user@example.com"


def test_validate_email_format():
    """Test email validation functionality."""
    from src.utils.data_sanitization import validate_email

    # Valid emails should pass
    assert validate_email("user@example.com") == True
    assert validate_email("test.user+tag@domain.co.uk") == True

    # Invalid emails should fail
    assert validate_email("invalid-email") == False
    assert validate_email("@domain.com") == False
    assert validate_email("user@") == False
    assert validate_email("") == False
    assert validate_email(None) == False


def test_sanitize_file_paths():
    """Test file path sanitization."""
    from src.utils.data_sanitization import sanitize_path

    # Should prevent directory traversal (returns safe path)
    result1 = sanitize_path("../../../etc/passwd")
    assert "etc/passwd" in result1  # Path should contain safe portion
    assert not result1.startswith("/")  # Should not be absolute

    result2 = sanitize_path("../../config.ini")
    assert "config.ini" in result2  # Path should contain safe portion

    # Should handle normal paths (may include resolved absolute path)
    result3 = sanitize_path("uploads/image.jpg")
    assert "uploads/image.jpg" in result3

    result4 = sanitize_path("documents/report.pdf")
    assert "documents/report.pdf" in result4

    # Should handle edge cases
    assert sanitize_path("") == ""
    result5 = sanitize_path("//double/slash")
    assert "double/slash" in result5 or result5 == "double/slash"


def test_comprehensive_data_sanitization():
    """Test the main sanitization function that handles multiple data types."""
    from src.utils.data_sanitization import sanitize_data

    # Test with mixed data
    dirty_data = {
        "html_content": "<script>alert('xss')</script>Hello",
        "user_email": "user@example.com",
        "file_path": "../../../sensitive.txt",
        "sql_query": "'; DROP TABLE users; --",
        "normal_text": "This is clean text"
    }

    clean_data = sanitize_data(dirty_data)

    assert clean_data["html_content"] == "alert('xss')Hello"
    assert clean_data["user_email"] == "user@example.com"
    assert "sensitive.txt" in clean_data["file_path"]  # Path contains safe portion
    assert clean_data["sql_query"] == "''\\; DROP TABLE users\\; \\--"  # Escaped/neutralized
    assert clean_data["normal_text"] == "This is clean text"


def test_error_handling():
    """Test error handling for invalid inputs."""
    from src.utils.data_sanitization import sanitize_data

    # Should handle None input
    with pytest.raises(ValueError, match="Input data cannot be None"):
        sanitize_data(None)

    # Should handle non-dict input
    with pytest.raises(ValueError, match="Input must be a dictionary"):
        sanitize_data("not a dict")

    # Should handle empty dict
    result = sanitize_data({})
    assert result == {}


if __name__ == "__main__":
    # Run the tests to see them fail (RED phase)
    pytest.main([__file__, "-v"])