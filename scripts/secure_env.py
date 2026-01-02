#!/usr/bin/env python3
"""
Secure environment loader with python-dotenv support

Loads API keys from .env file with security checks.
Falls back to system environment variables if .env not available.
"""

import os
from pathlib import Path


def load_env():
    """Load environment variables securely"""
    try:
        from dotenv import load_dotenv

        # Look for .env file in project root
        env_path = Path(__file__).parent.parent / ".env"

        if env_path.exists():
            load_dotenv(env_path)
            print("🔒 Loaded environment from .env file")

            # Security check: warn if .env has wrong permissions
            if os.name != "nt":  # Unix-like systems
                stat_info = os.stat(env_path)
                mode = stat_info.st_mode & 0o777
                if mode & 0o077:  # Check if group/others can read
                    print("⚠️  WARNING: .env file has insecure permissions!")
                    print(f"   Current: {oct(mode)}")
                    print(f"   Run: chmod 600 {env_path}")
        else:
            print("ℹ️  No .env file found, using system environment")

    except ImportError:
        # python-dotenv not installed, use system env vars
        print("ℹ️  python-dotenv not installed, using system environment")
        print("   Tip: pip install python-dotenv for .env file support")


def get_api_key(provider: str = "openai") -> str:
    """
    Get API key securely with validation

    Args:
        provider: 'openai' or 'anthropic'

    Returns:
        API key string

    Raises:
        ValueError: If key not found or invalid
    """
    load_env()

    key_name = f"{provider.upper()}_API_KEY"
    api_key = os.environ.get(key_name)

    if not api_key:
        raise ValueError(
            f"[SECURITY] {key_name} not set.\n"
            f"Options:\n"
            f"  1. Create .env file: cp .env.example .env (then edit)\n"
            f"  2. Export directly: export {key_name}='sk-...'\n"
            f"  3. Use secrets manager in production"
        )

    # Basic validation
    if provider == "openai" and not api_key.startswith("sk-"):
        raise ValueError("[SECURITY] Invalid OpenAI API key format")
    elif provider == "anthropic" and not api_key.startswith("sk-ant-"):
        raise ValueError("[SECURITY] Invalid Anthropic API key format")

    # Mask key in logs
    masked = f"{api_key[:8]}...{api_key[-4:]}"
    print(f"🔑 Using {provider} API key: {masked}")

    return api_key


if __name__ == "__main__":
    # Test the loader
    print("Testing secure environment loader...\n")

    try:
        key = get_api_key("openai")
        print("✅ OpenAI key loaded successfully")
    except ValueError as e:
        print(f"❌ {e}")

    try:
        key = get_api_key("anthropic")
        print("✅ Anthropic key loaded successfully")
    except ValueError:
        print("ℹ️  Anthropic key not set (optional)")
