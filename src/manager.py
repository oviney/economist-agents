#!/usr/bin/env python3
"""
Mission Control - Manager Agent Orchestration

This script provides the command-line interface for the Manager Agent,
which orchestrates high-level missions across the Economist Agents system.

Usage:
    python3 src/manager.py --mission "Deploy Story 10 Stage 3 migration"
    ./run.sh --mission "Execute Sprint 10 Story 11"

The Manager Agent uses AgentRegistry to load crew configuration and
execute complex multi-agent missions.
"""

import argparse
import sys
from pathlib import Path

# Add project root to Python path for module imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.agent_registry import AgentRegistry  # noqa: E402


def main():
    """
    Main entry point for Mission Control.

    Parses command-line arguments and executes the specified mission
    using the Manager Agent crew from the AgentRegistry.
    """
    parser = argparse.ArgumentParser(
        description="Mission Control - Manager Agent Orchestration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 src/manager.py --mission "Deploy Story 10 changes to production"
  python3 src/manager.py --mission "Execute Sprint 10 Story 11 tasks"
  ./run.sh --mission "Coordinate Stage 3 crew migration"
        """,
    )

    parser.add_argument(
        "--mission",
        type=str,
        required=True,
        help="Mission description for the Manager Agent to execute",
    )

    parser.add_argument(
        "--verbose", action="store_true", help="Enable verbose output for debugging"
    )

    args = parser.parse_args()

    # Validate mission is not empty
    if not args.mission.strip():
        print("Error: Mission description cannot be empty", file=sys.stderr)
        sys.exit(1)

    try:
        # Get the manager crew from AgentRegistry
        if args.verbose:
            print("Mission Control: Initializing Manager Agent...")
            print(f"Mission: {args.mission}")

        manager_crew = AgentRegistry.get_crew("manager")

        if args.verbose:
            print(f"Manager crew loaded: {manager_crew}")

        # Execute the mission
        print(f"\n{'='*70}")
        print("MISSION CONTROL: Executing Mission")
        print(f"{'='*70}")
        print(f"Mission: {args.mission}")
        print(f"{'='*70}\n")

        result = manager_crew.kickoff(inputs={"mission": args.mission})

        # Display results
        print(f"\n{'='*70}")
        print("MISSION CONTROL: Mission Complete")
        print(f"{'='*70}")
        print(f"\nResult:\n{result}")
        print(f"\n{'='*70}\n")

        return 0

    except Exception as e:
        print(f"\nMission Control Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
