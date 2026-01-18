#!/usr/bin/env python3
import sys
from pathlib import Path

# Add the project root to the Python path (same as economist_agent.py)
sys.path.insert(0, str(Path(__file__).parent))

print("Testing import sequence in debug_test.py")
print(f"Python executable: {sys.executable}")
print(f"PYTHONPATH includes: {str(Path(__file__).parent)}")

# Test the exact imports that happen in economist_agent.py
print("\n1. Testing StyleMemoryTool import...")
try:
    from src.tools.style_memory_tool import StyleMemoryTool

    print("✅ StyleMemoryTool imported successfully")

    # Test actual usage
    print("\n2. Testing StyleMemoryTool instantiation...")
    try:
        tool = StyleMemoryTool()
        print("✅ StyleMemoryTool instantiated successfully")
    except Exception as e:
        print(f"❌ StyleMemoryTool instantiation failed: {e}")

except ImportError as e:
    print(f"❌ StyleMemoryTool import failed: {e}")

print("\nDone.")
