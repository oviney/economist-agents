#!/bin/bash
# Quick test of governance system

echo "══════════════════════════════════════════════════════════"
echo "🧪 Testing Governance System"
echo "══════════════════════════════════════════════════════════"
echo ""

# Show help
echo "1️⃣  Showing CLI options:"
echo ""
cd /Users/ouray.viney/code/economist-agents
.venv/bin/python scripts/economist_agent.py --help
echo ""

echo "══════════════════════════════════════════════════════════"
echo "2️⃣  File Structure:"
echo ""
echo "Governance module:"
ls -lh scripts/governance.py
echo ""
echo "Documentation:"
ls -lh docs/GOVERNANCE_GUIDE.md
echo ""

echo "══════════════════════════════════════════════════════════"
echo "3️⃣  Quick Validation:"
echo ""
python3 -c "
import sys
sys.path.insert(0, 'scripts')
from governance import GovernanceTracker

# Test governance tracker creation
tracker = GovernanceTracker('test_output/governance')
print(f'✅ GovernanceTracker created')
print(f'   Session ID: {tracker.session_id}')
print(f'   Session dir: {tracker.session_dir}')

# Test logging
tracker.log_agent_output('test_agent', {'result': 'test'}, {'key': 'value'})
print(f'✅ Agent output logged')

# Test decision
tracker.log_decision('approval', 'approve', 'Test approval', {'stage': 'test'})
print(f'✅ Decision logged')

# Test report
tracker.generate_report()
print(f'✅ Report generated')

print(f'\\n📁 Test files created:')
import os
for root, dirs, files in os.walk('test_output/governance'):
    level = root.replace('test_output/governance', '').count(os.sep)
    indent = ' ' * 2 * level
    print(f'{indent}{os.path.basename(root)}/')
    subindent = ' ' * 2 * (level + 1)
    for file in files:
        print(f'{subindent}{file}')
"
echo ""

echo "══════════════════════════════════════════════════════════"
echo "4️⃣  Key Features:"
echo ""
echo "✅ Interactive approval gates"
echo "✅ JSON output saving for all agents"
echo "✅ Audit trail (decisions.jsonl)"
echo "✅ Human-readable reports"
echo "✅ Session-based tracking"
echo "✅ CLI flags: --interactive, --governance-dir"
echo ""

echo "══════════════════════════════════════════════════════════"
echo "🎉 Ready to Use!"
echo ""
echo "Try it:"
echo "  .venv/bin/python scripts/economist_agent.py --interactive"
echo ""
echo "Documentation:"
echo "  docs/GOVERNANCE_GUIDE.md"
echo "══════════════════════════════════════════════════════════"
