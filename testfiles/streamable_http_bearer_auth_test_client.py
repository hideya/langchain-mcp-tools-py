#!/usr/bin/env python3
"""
Test Client with Auto Token Loading
"""

import asyncio
import logging
import time
from pathlib import Path
from langchain_mcp_tools import convert_mcp_to_langchain_tools

# Configure logging
logging.basicConfig(level=logging.INFO)

TOKEN_FILE = Path(".test_token")

def load_test_token() -> str | None:
    """Load test token from file with validation."""
    try:
        if not TOKEN_FILE.exists():
            print(f"❌ Token file {TOKEN_FILE} not found.")
            print("   Make sure the test server is running!")
            return None
        
        # Check if file is recent (within last hour)
        file_age = time.time() - TOKEN_FILE.stat().st_mtime
        if file_age > 3600:  # 1 hour
            print(f"⚠️  Token file is {file_age/60:.1f} minutes old, might be expired")
        
        token = TOKEN_FILE.read_text().strip()
        if not token:
            print("❌ Token file is empty")
            return None
            
        print(f"✅ Loaded token from {TOKEN_FILE} (age: {file_age/60:.1f} minutes)")
        return token
        
    except Exception as e:
        print(f"❌ Failed to load token: {e}")
        return None

def wait_for_token_file(timeout: int = 30) -> str | None:
    """Wait for token file to appear (useful if client starts before server)."""
    print(f"⏳ Waiting for token file {TOKEN_FILE} (timeout: {timeout}s)...")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        token = load_test_token()
        if token:
            return token
        time.sleep(1)
    
    print(f"⏰ Timeout waiting for token file")
    return None

async def test_valid_authentication(token: str):
    """Test valid JWT token authentication."""
    print("✅ Test 1: Valid JWT Token")
    print("=" * 50)
    
    server_config = {
        "auth-server": {
            "url": "http://127.0.0.1:8001/mcp",
            "headers": {"Authorization": f"Bearer {token}"},
            "timeout": 10.0
        }
    }
    
    try:
        tools, cleanup = await convert_mcp_to_langchain_tools(server_config)
        print(f"✅ Connected to auth server with {len(tools)} tools")
        
        # List available tools
        print("\n🛠️  Available Tools:")
        for tool in tools:
            print(f"  • {tool.name}: {tool.description}")
        
        # Test a few tools
        if tools:
            print("\n🔍 Testing Authenticated Tools:")
            
            # Test authenticated_echo tool
            echo_tool = next((t for t in tools if t.name == "authenticated_echo"), None)
            if echo_tool:
                result = await echo_tool.ainvoke({"message": "Hello Auto-Token!"})
                print(f"  authenticated_echo('Hello Auto-Token!') = {result}")
            
            # Test secure_add tool
            add_tool = next((t for t in tools if t.name == "secure_add"), None)
            if add_tool:
                result = await add_tool.ainvoke({"a": 42, "b": 8})
                print(f"  secure_add(42, 8) = {result}")
        
        await cleanup()
        print("✅ Valid auth test completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Valid auth test failed: {e}")
        return False

async def main():
    """Run authentication tests with auto token loading."""
    print("🧪 Testing langchain-mcp-tools with Auto Token Loading")
    print("=" * 70)
    
    # Try to load token, wait if necessary
    token = load_test_token()
    if not token:
        print("🔄 Token not found, waiting for server to start...")
        token = wait_for_token_file()
    
    if not token:
        print("\n❌ Could not load test token!")
        print("Please ensure the test server is running:")
        print("  uv run testfiles/streamable_http_bearer_auth_test_server.py")
        return
    
    print(f"🔑 Using token: {token[:50]}...")
    print("=" * 70)
    
    # Run tests
    success = await test_valid_authentication(token)
    
    if success:
        print("\n🎉 All tests completed successfully!")
    else:
        print("\n❌ Some tests failed!")

if __name__ == "__main__":
    asyncio.run(main())
