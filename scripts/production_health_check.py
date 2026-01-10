#!/usr/bin/env python3
"""
Production Health Check for Sprint 15 Deployment

Validates health of all Sprint 14 components:
- Flow Orchestration (EconomistContentFlow)
- Style Memory RAG (StyleMemoryTool)
- ROI Telemetry (ROITracker)

Returns JSON status suitable for monitoring systems.
Exit codes: 0=healthy, 1=degraded, 2=unhealthy
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path


def check_flow_health() -> dict:
    """Check Flow orchestration health"""
    try:
        from src.economist_agents.flow import EconomistContentFlow

        # Test instantiation
        _ = EconomistContentFlow()  # Test instantiation only
        return {
            "status": "healthy",
            "available": True,
            "version": "1.0",
            "details": "Flow orchestration operational",
        }
    except ImportError as e:
        return {
            "status": "degraded",
            "available": False,
            "fallback": "WORKFLOW_SEQUENCE",
            "details": f"Flow not available: {e}",
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "available": False,
            "error": str(e),
            "details": "Flow initialization failed",
        }


def check_rag_health() -> dict:
    """Check RAG health"""
    try:
        from src.tools.style_memory_tool import StyleMemoryTool

        # Test instantiation
        tool = StyleMemoryTool()

        # Test query (if ChromaDB available)
        start_time = time.time()
        _ = tool.query_patterns("test query", top_k=1)  # Test query execution
        latency_ms = (time.time() - start_time) * 1000

        return {
            "status": "healthy" if latency_ms < 500 else "degraded",
            "available": True,
            "latency_ms": round(latency_ms, 2),
            "query_test": "pass",
            "details": f"RAG operational, {latency_ms:.2f}ms latency",
        }
    except ImportError as e:
        return {
            "status": "degraded",
            "available": False,
            "fallback": "Editor without RAG",
            "details": f"RAG not available: {e}",
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "available": False,
            "error": str(e),
            "details": "RAG query failed",
        }


def check_roi_health() -> dict:
    """Check ROI Telemetry health"""
    try:
        from src.telemetry.roi_tracker import ROITracker

        # Test instantiation
        _ = ROITracker()  # Test instantiation only

        # Test file accessibility
        log_file = Path("execution_roi.json")
        writable = log_file.parent.is_dir()

        return {
            "status": "healthy",
            "available": True,
            "log_file": str(log_file),
            "writable": writable,
            "details": "ROI telemetry operational",
        }
    except ImportError as e:
        return {
            "status": "degraded",
            "available": False,
            "fallback": "No telemetry",
            "details": f"ROI tracker not available: {e}",
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "available": False,
            "error": str(e),
            "details": "ROI tracker initialization failed",
        }


def check_environment() -> dict:
    """Check Python environment health"""
    import platform

    try:
        python_version = platform.python_version()
        is_correct = python_version.startswith("3.13")

        # Check virtual environment
        venv_path = Path(".venv/bin/python3")
        venv_active = venv_path.exists()

        # Count installed packages
        try:
            import pkg_resources

            packages = len(list(pkg_resources.working_set))
        except Exception:
            packages = "unknown"

        return {
            "status": "healthy" if is_correct else "degraded",
            "python_version": python_version,
            "correct_version": is_correct,
            "venv_active": venv_active,
            "packages_installed": packages,
            "details": f"Python {python_version}, {packages} packages",
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "details": "Environment check failed",
        }


def check_file_system() -> dict:
    """Check file system health (output directories)"""
    try:
        output_dir = Path("output")
        charts_dir = output_dir / "charts"
        logs_dir = Path("logs")

        # Create directories if missing
        output_dir.mkdir(exist_ok=True)
        charts_dir.mkdir(exist_ok=True)
        logs_dir.mkdir(exist_ok=True)

        # Test writability
        test_file = logs_dir / ".health_check_test"
        try:
            test_file.touch()
            test_file.unlink()
            writable = True
        except Exception:
            writable = False

        return {
            "status": "healthy" if writable else "degraded",
            "output_dir_exists": output_dir.exists(),
            "charts_dir_exists": charts_dir.exists(),
            "logs_dir_writable": writable,
            "details": "File system operational",
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "details": "File system check failed",
        }


def check_dependencies() -> dict:
    """Check critical dependencies"""
    dependencies = {
        "anthropic": "LLM API client",
        "matplotlib": "Chart generation",
        "crewai": "Agent orchestration",
        "chromadb": "Vector database",
    }

    missing = []
    available = []

    for dep, description in dependencies.items():
        try:
            __import__(dep)
            available.append({"name": dep, "description": description})
        except ImportError:
            missing.append({"name": dep, "description": description})

    total = len(dependencies)
    available_count = len(available)

    return {
        "status": "healthy"
        if available_count == total
        else "degraded"
        if available_count > 0
        else "unhealthy",
        "total": total,
        "available": available_count,
        "missing": len(missing),
        "available_deps": available,
        "missing_deps": missing,
        "details": f"{available_count}/{total} critical dependencies available",
    }


def overall_health_status(checks: dict) -> str:
    """Determine overall health from component checks"""
    statuses = [check["status"] for check in checks.values()]

    if "unhealthy" in statuses:
        return "unhealthy"
    elif "degraded" in statuses:
        return "degraded"
    else:
        return "healthy"


def check_health(verbose: bool = False) -> dict:
    """Production health check - main entry point"""
    timestamp = datetime.now().isoformat()

    # Run all checks
    checks = {
        "environment": check_environment(),
        "file_system": check_file_system(),
        "dependencies": check_dependencies(),
        "flow": check_flow_health(),
        "rag": check_rag_health(),
        "roi": check_roi_health(),
    }

    # Determine overall status
    overall_status = overall_health_status(checks)

    status = {
        "status": overall_status,
        "version": "sprint-15",
        "timestamp": timestamp,
        "components": checks,
    }

    if verbose:
        # Add detailed component info
        status["summary"] = {
            "healthy": sum(1 for c in checks.values() if c["status"] == "healthy"),
            "degraded": sum(1 for c in checks.values() if c["status"] == "degraded"),
            "unhealthy": sum(1 for c in checks.values() if c["status"] == "unhealthy"),
            "total": len(checks),
        }

    return status


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Production health check")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Verbose output with summary"
    )
    parser.add_argument(
        "--component",
        "-c",
        choices=["environment", "file_system", "dependencies", "flow", "rag", "roi"],
        help="Check specific component only",
    )
    args = parser.parse_args()

    # Run health check
    if args.component:
        # Check specific component
        check_functions = {
            "environment": check_environment,
            "file_system": check_file_system,
            "dependencies": check_dependencies,
            "flow": check_flow_health,
            "rag": check_rag_health,
            "roi": check_roi_health,
        }
        result = check_functions[args.component]()
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["status"] == "healthy" else 1)
    else:
        # Full health check
        health = check_health(verbose=args.verbose)
        print(json.dumps(health, indent=2))

        # Exit code based on status
        exit_code = {
            "healthy": 0,
            "degraded": 1,
            "unhealthy": 2,
        }
        sys.exit(exit_code.get(health["status"], 2))


if __name__ == "__main__":
    main()
