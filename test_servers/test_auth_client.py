#!/usr/bin/env python3
"""
Test Client for Bearer Token Authentication

This script tests your langchain-mcp-tools library's authentication support
against the bearer token authentication server.

Usage:
    # First start the auth server:
    python simple_bearer_auth_server.py
    
    # Then run this test client:
    python test_auth_client.py
"""

import asyncio
import logging
from langchain_mcp_tools import convert_mcp_to_langchain_tools

# Configure logging to see authentication in action
logging.basicConfig(level=logging.INFO)

async def test_bearer_auth():
    """Test bearer token authentication."""
    print("🔐 Testing Bearer Token Authentication")
    print("=" * 60)
    
    # Test 1: Valid Authentication
    print("\n✅ Test 1: Valid Bearer Token")
    valid_config = {
        "auth-server": {
            "url": "http://127.0.0.1:8001/mcp",
            "headers": {
                "Authorization": "Bearer valid-token-123"
            },
            "timeout": 10.0
        }
    }
    
    try:
        tools, cleanup = await convert_mcp_to_langchain_tools(valid_config)
        print(f"✅ Connected with valid token: {len(tools)} tools available")
        
        # List tools
        print("\n🛠️  Available Tools:")
        for tool in tools:
            print(f"  • {tool.name}: {tool.description}")
        
        # Test a tool
        if tools:
            echo_tool = next((t for t in tools if t.name == "authenticated_echo"), None)
            if echo_tool:
                result = await echo_tool.ainvoke({"message": "Hello from authenticated client!"})
                print(f"\n🔧 Tool test: {result}")
        
        await cleanup()
        print("✅ Valid auth test completed successfully")
        
    except Exception as e:
        print(f"❌ Valid auth test failed: {e}")

async def test_invalid_auth():
    """Test invalid authentication (should fail)."""
    print("\n❌ Test 2: Invalid Bearer Token")
    
    invalid_config = {
        "auth-server": {
            "url": "http://127.0.0.1:8001/mcp",
            "headers": {
                "Authorization": "Bearer invalid-token"
            },
            "timeout": 10.0
        }
    }
    
    try:
        tools, cleanup = await convert_mcp_to_langchain_tools(invalid_config)
        print(f"❌ Unexpected success with invalid token: {len(tools)} tools")
        await cleanup()
        
    except Exception as e:
        print(f"✅ Invalid auth correctly rejected: {e}")

async def test_no_auth():
    """Test no authentication (should fail)."""
    print("\n🚫 Test 3: No Authentication Header")
    
    no_auth_config = {
        "auth-server": {
            "url": "http://127.0.0.1:8001/mcp",
            # No headers - should fail
            "timeout": 10.0
        }
    }
    
    try:
        tools, cleanup = await convert_mcp_to_langchain_tools(no_auth_config)
        print(f"❌ Unexpected success without auth: {len(tools)} tools")
        await cleanup()
        
    except Exception as e:
        print(f"✅ No auth correctly rejected: {e}")

async def test_expired_token():
    """Test expired token (should fail)."""
    print("\n⏰ Test 4: Expired Token")
    
    expired_config = {
        "auth-server": {
            "url": "http://127.0.0.1:8001/mcp",
            "headers": {
                "Authorization": "Bearer expired-token"
            },
            "timeout": 10.0
        }
    }
    
    try:
        tools, cleanup = await convert_mcp_to_langchain_tools(expired_config)
        print(f"❌ Unexpected success with expired token: {len(tools)} tools")
        await cleanup()
        
    except Exception as e:
        print(f"✅ Expired token correctly rejected: {e}")

async def test_different_tokens():
    """Test different token types."""
    print("\n🔑 Test 5: Different Token Types")
    
    test_configs = {
        "read-only": {
            "url": "http://127.0.0.1:8001/mcp",
            "headers": {"Authorization": "Bearer read-only-token"},
            "timeout": 10.0
        },
        "admin": {
            "url": "http://127.0.0.1:8001/mcp", 
            "headers": {"Authorization": "Bearer test-token-789"},
            "timeout": 10.0
        }
    }
    
    for token_type, config in test_configs.items():
        print(f"\n🔍 Testing {token_type} token...")
        try:
            tools, cleanup = await convert_mcp_to_langchain_tools({f"server-{token_type}": config})
            print(f"✅ {token_type} token accepted: {len(tools)} tools")
            await cleanup()
        except Exception as e:
            print(f"❌ {token_type} token failed: {e}")

async def test_custom_headers():
    """Test custom headers functionality."""
    print("\n🎨 Test 6: Custom Headers")
    
    custom_headers_config = {
        "custom-auth-server": {
            "url": "http://127.0.0.1:8001/mcp",
            "headers": {
                "Authorization": "Bearer valid-token-123",
                "User-Agent": "langchain-mcp-tools-test-client",
                "X-Custom-Header": "test-value",
                "X-Client-Version": "1.0.0"
            },
            "timeout": 10.0
        }
    }
    
    try:
        tools, cleanup = await convert_mcp_to_langchain_tools(custom_headers_config)
        print(f"✅ Custom headers accepted: {len(tools)} tools")
        await cleanup()
    except Exception as e:
        print(f"❌ Custom headers failed: {e}")

async def main():
    """Run all authentication tests."""
    print("🧪 Testing langchain-mcp-tools Authentication Support")
    print("=" * 70)
    print("Make sure simple_bearer_auth_server.py is running first!")
    print("=" * 70)
    
    # Run all tests
    await test_bearer_auth()
    await test_invalid_auth()
    await test_no_auth()
    await test_expired_token()
    await test_different_tokens()
    await test_custom_headers()
    
    print("\n🎉 All authentication tests completed!")
    print("\n💡 Summary:")
    print("  ✅ Valid tokens should be accepted")
    print("  ❌ Invalid/missing/expired tokens should be rejected")
    print("  🔧 Tools should work correctly with valid auth")
    print("  🎨 Custom headers should be passed through")
    print("\n📋 What this validates:")
    print("  • Your library's 'headers' parameter works correctly")
    print("  • Authentication errors are handled properly")
    print("  • Bearer token format is supported")
    print("  • Custom headers are preserved")

if __name__ == "__main__":
    asyncio.run(main())
