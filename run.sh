#!/bin/bash
# 1. Enforce Venv (Stop "pip install" loops)
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "Error: .venv not found. Please run setup first."
    exit 1
fi

# 2. Fix Imports (Inject Root Project path)
export PYTHONPATH=$PYTHONPATH:$(pwd)

# 3. Execute the passed script
python3 "$@"
