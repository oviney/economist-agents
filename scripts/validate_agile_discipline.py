#!/usr/bin/env python3
"""
Validation Script: Agile Discipline Enforcement

Verifies that AGILE_MINDSET is properly injected into all agents.
"""

import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

from agent_registry import AgentRegistry


def validate_agile_discipline():
    """Validate that all agents have Agile discipline injected."""
    print("=" * 70)
    print("AGILE DISCIPLINE VALIDATION")
    print("=" * 70)
    print()

    registry = AgentRegistry()
    agents = registry.list_agents()

    print(f"📋 Testing {len(agents)} agents...\n")

    all_valid = True
    for agent_name in agents:
        try:
            agent = registry.get_agent(agent_name)
            backstory = agent["backstory"]

            # Check if AGILE_MINDSET is present in backstory
            has_discipline = "YOU ARE AN AGILE TEAM MEMBER" in backstory
            has_no_ticket = "NO TICKET, NO WORK" in backstory
            has_dod = "DEFINITION OF DONE" in backstory
            has_status = "STATUS UPDATES" in backstory

            if has_discipline and has_no_ticket and has_dod and has_status:
                print(f"✅ {agent_name:25s} - Agile discipline enforced")
            else:
                print(f"❌ {agent_name:25s} - Missing Agile discipline!")
                all_valid = False

        except Exception as e:
            print(f"⚠️  {agent_name:25s} - Error: {e}")
            all_valid = False

    print()
    print("=" * 70)
    if all_valid:
        print("✅ SUCCESS: All agents have Agile discipline enforced")
    else:
        print("❌ FAILURE: Some agents missing Agile discipline")
    print("=" * 70)

    return all_valid


if __name__ == "__main__":
    success = validate_agile_discipline()
    sys.exit(0 if success else 1)
