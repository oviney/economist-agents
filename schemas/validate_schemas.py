#!/usr/bin/env python3
"""
JSON Schema Validator for Pipeline Stages

Validates JSON intermediate files against their schemas to catch
data flow issues early.

Usage:
    python3 schemas/validate_schemas.py content_queue.json
    python3 schemas/validate_schemas.py board_decision.json
    python3 schemas/validate_schemas.py --all
"""

import json
import sys
from pathlib import Path


def validate_json_file(json_path: Path, schema_path: Path) -> tuple[bool, list[str]]:
    """
    Validate a JSON file against its schema.

    Returns:
        (is_valid, error_messages)
    """
    errors = []

    # Load JSON file
    try:
        with open(json_path) as f:
            data = json.load(f)
    except FileNotFoundError:
        return False, [f"File not found: {json_path}"]
    except json.JSONDecodeError as e:
        return False, [f"Invalid JSON: {e}"]

    # Load schema
    try:
        with open(schema_path) as f:
            schema = json.load(f)
    except FileNotFoundError:
        return False, [f"Schema not found: {schema_path}"]
    except json.JSONDecodeError as e:
        return False, [f"Invalid schema JSON: {e}"]

    # Try to import jsonschema for full validation
    try:
        import jsonschema

        try:
            jsonschema.validate(instance=data, schema=schema)
            return True, []
        except jsonschema.ValidationError as e:
            return False, [f"Validation error: {e.message}"]
        except jsonschema.SchemaError as e:
            return False, [f"Schema error: {e.message}"]
    except ImportError:
        # Fallback to basic validation if jsonschema not available
        return _basic_validation(data, schema)


def _basic_validation(data: dict, schema: dict) -> tuple[bool, list[str]]:
    """
    Basic validation without jsonschema library.
    Checks required fields and types.
    """
    errors = []

    # Check type
    if schema.get("type") == "object" and not isinstance(data, dict):
        errors.append(f"Expected object, got {type(data).__name__}")
        return False, errors

    # Check required fields
    required = schema.get("required", [])
    for field in required:
        if field not in data:
            errors.append(f"Missing required field: {field}")

    # Check properties
    properties = schema.get("properties", {})
    for key, value in data.items():
        if key in properties:
            prop_schema = properties[key]
            expected_type = prop_schema.get("type")

            # Type checking
            if expected_type == "string" and not isinstance(value, str):
                errors.append(
                    f"Field '{key}' should be string, got {type(value).__name__}"
                )
            elif expected_type == "integer" and not isinstance(value, int):
                errors.append(
                    f"Field '{key}' should be integer, got {type(value).__name__}"
                )
            elif expected_type == "number" and not isinstance(value, (int, float)):
                errors.append(
                    f"Field '{key}' should be number, got {type(value).__name__}"
                )
            elif expected_type == "array" and not isinstance(value, list):
                errors.append(
                    f"Field '{key}' should be array, got {type(value).__name__}"
                )
            elif expected_type == "object" and not isinstance(value, dict):
                errors.append(
                    f"Field '{key}' should be object, got {type(value).__name__}"
                )

    return len(errors) == 0, errors


def validate_content_queue(file_path: Path = None) -> bool:
    """Validate content_queue.json"""
    if file_path is None:
        file_path = Path(__file__).parent.parent / "content_queue.json"

    schema_path = Path(__file__).parent / "content_queue_schema.json"

    is_valid, errors = validate_json_file(file_path, schema_path)

    if is_valid:
        print(f"✅ {file_path.name} is valid")
    else:
        print(f"❌ {file_path.name} validation failed:")
        for error in errors:
            print(f"   • {error}")

    return is_valid


def validate_board_decision(file_path: Path = None) -> bool:
    """Validate board_decision.json"""
    if file_path is None:
        file_path = Path(__file__).parent.parent / "board_decision.json"

    schema_path = Path(__file__).parent / "board_decision_schema.json"

    is_valid, errors = validate_json_file(file_path, schema_path)

    if is_valid:
        print(f"✅ {file_path.name} is valid")
    else:
        print(f"❌ {file_path.name} validation failed:")
        for error in errors:
            print(f"   • {error}")

    return is_valid


def validate_all():
    """Validate all pipeline intermediate files"""
    results = []

    print("\n" + "=" * 60)
    print("VALIDATING PIPELINE DATA FILES")
    print("=" * 60 + "\n")

    results.append(("content_queue.json", validate_content_queue()))
    results.append(("board_decision.json", validate_board_decision()))

    print("\n" + "=" * 60)
    passed = sum(1 for _, valid in results if valid)
    total = len(results)
    print(f"RESULTS: {passed}/{total} files valid")
    print("=" * 60 + "\n")

    return all(valid for _, valid in results)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Validate JSON files against schemas")
    parser.add_argument("file", nargs="?", help="JSON file to validate")
    parser.add_argument(
        "--all", action="store_true", help="Validate all pipeline files"
    )

    args = parser.parse_args()

    if args.all:
        success = validate_all()
        sys.exit(0 if success else 1)
    elif args.file:
        file_path = Path(args.file)

        if "content_queue" in file_path.name:
            success = validate_content_queue(file_path)
        elif "board_decision" in file_path.name:
            success = validate_board_decision(file_path)
        else:
            print(f"Unknown file type: {file_path.name}")
            print("Expected: content_queue.json or board_decision.json")
            sys.exit(1)

        sys.exit(0 if success else 1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
