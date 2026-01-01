#!/usr/bin/env python3
"""
Quick Setup Test - Verify API keys and LLM client

Tests:
1. Environment loading (.env or system vars)
2. API key presence and format
3. LLM client creation
4. Basic API call

Usage:
    python3 scripts/test_setup.py
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from llm_client import create_llm_client, call_llm
    from secure_env import load_env, get_api_key
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("\nMake sure you're in the project root directory:")
    print("  cd /path/to/economist-agents")
    print("  python3 scripts/test_setup.py")
    sys.exit(1)


def test_environment():
    """Test 1: Check environment variables"""
    print("="*60)
    print("TEST 1: Environment Loading")
    print("="*60)
    
    # Load .env file if present
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        print(f"✅ Found .env file: {env_file}")
        load_env()
    else:
        print("ℹ️  No .env file found (using system environment variables)")
    
    # Check for API keys
    openai_key = os.environ.get('OPENAI_API_KEY', '').strip()
    anthropic_key = os.environ.get('ANTHROPIC_API_KEY', '').strip()
    
    if openai_key:
        masked = get_api_key('openai')
        print(f"✅ OPENAI_API_KEY found: {masked}")
        model = os.environ.get('OPENAI_MODEL', 'gpt-4o')
        print(f"   Model: {model}")
    
    if anthropic_key:
        masked = get_api_key('anthropic')
        print(f"✅ ANTHROPIC_API_KEY found: {masked}")
        model = os.environ.get('ANTHROPIC_MODEL', 'claude-sonnet-4-20250514')
        print(f"   Model: {model}")
    
    if not openai_key and not anthropic_key:
        print("❌ No API keys found!")
        print("\nSetup instructions:")
        print("1. Run: ./scripts/setup_env.sh")
        print("2. Edit .env file: nano .env")
        print("3. Add your API key")
        print("4. Run this test again")
        return False
    
    print()
    return True


def test_client_creation():
    """Test 2: Create LLM client"""
    print("="*60)
    print("TEST 2: LLM Client Creation")
    print("="*60)
    
    try:
        client = create_llm_client()
        print(f"✅ Client created successfully")
        print(f"   Provider: {client.provider}")
        print(f"   Model: {client.model}")
        print()
        return client
    except Exception as e:
        print(f"❌ Failed to create client: {e}")
        print()
        return None


def test_api_call(client):
    """Test 3: Make a basic API call"""
    print("="*60)
    print("TEST 3: API Call")
    print("="*60)
    print("Making test call (this may take a few seconds)...")
    
    try:
        response = call_llm(
            client,
            "You are a helpful assistant.",
            "What is 2+2? Respond with just the number.",
            max_tokens=10
        )
        
        print(f"✅ API call successful!")
        print(f"   Response: {response.strip()}")
        print()
        return True
    except Exception as e:
        print(f"❌ API call failed: {e}")
        print()
        
        # Provide helpful error messages
        if "authentication" in str(e).lower() or "api key" in str(e).lower():
            print("💡 This looks like an authentication error.")
            print("   Check that your API key is correct and active.")
            print("   Get your key from:")
            if client.provider == 'openai':
                print("   https://platform.openai.com/api-keys")
            else:
                print("   https://console.anthropic.com/settings/keys")
        elif "rate limit" in str(e).lower():
            print("💡 You hit a rate limit. Wait a moment and try again.")
        elif "insufficient" in str(e).lower() or "quota" in str(e).lower():
            print("💡 Looks like you're out of credits.")
            print("   Add credits to your account on the provider's dashboard.")
        
        return False


def main():
    """Run all tests"""
    print("\n🧪 Economist Agents - Setup Test\n")
    
    # Test 1: Environment
    if not test_environment():
        sys.exit(1)
    
    # Test 2: Client creation
    client = test_client_creation()
    if not client:
        sys.exit(1)
    
    # Test 3: API call
    success = test_api_call(client)
    
    # Summary
    print("="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    if success:
        print("✅ ALL TESTS PASSED!")
        print("\nYour setup is ready. Run the pipeline:")
        print("  python3 scripts/topic_scout.py")
        print("  python3 scripts/editorial_board.py")
        print("  python3 scripts/economist_agent.py")
    else:
        print("❌ SOME TESTS FAILED")
        print("\nFix the issues above and run this test again.")
        sys.exit(1)
    
    print()


if __name__ == "__main__":
    main()
