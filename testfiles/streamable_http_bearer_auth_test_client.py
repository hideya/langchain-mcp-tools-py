#!/usr/bin/env python3
"""
Test Client for FastMCP Bearer Authentication

This script tests your langchain-mcp-tools library against the FastMCP auth server.
It demonstrates proper JWT token authentication.

Usage:
    # First start the FastMCP auth server in another terminal:
    uv run testfiles/streamable_http_bearer_auth_test_server.py
    
    # Copy the test token from the server output, then run this client:
    uv run testfiles/streamable_http_bearer_auth_test_client.py
"""

import asyncio
import logging
from langchain_mcp_tools import convert_mcp_to_langchain_tools

# Configure logging to see the transport detection in action
logging.basicConfig(level=logging.INFO)

# 👇 PASTE THE TEST TOKEN FROM YOUR SERVER OUTPUT HERE
TEST_TOKEN = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ0ZXN0LWF1dGgtc2VydmVyIiwic3ViIjoidGVzdC11c2VyIiwiaWF0IjoxNzUwOTkxMjIwLCJleHAiOjE3NTA5OTQ4MjAsImF1ZCI6Im1jcC10ZXN0LWNsaWVudCJ9.uv2Za3LomYu4nJP1EYNHt6ZdzuJshF-iu5inCOuliiT6kiIm7EEj626n526rrTIIsYtXLq1HD57tf9G3m5JUH0YdRjx5RA492q70rIzYdArivC_QyzReXKkDO8KV2PB2yw36JPoNC87mZYQpLndcSNOKAlL2--UE7eZolvqni_T3sjlqdOjiDMS3NhzDbo4MYWw5cIhHBwO01Ruv3RRXyo6GJJ0NfwvAuhRAecOnnchJJ8iywRYVii6U4sOM0RPZueNghMgbubVbrsIpA7iMPPcVP_mj8VxTnKPtBeGCC2sxrWg8qm0psJ_bR72ZAtJIo1MvVGDOncqwppO08vQDIw"

async def test_valid_authentication():
    """Test valid JWT token authentication."""
    print("✅ Test 1: Valid JWT Token")
    print("=" * 50)
    
    server_config = {
        "auth-server": {
            "url": "http://127.0.0.1:8001/mcp",
            "headers": {"Authorization": f"Bearer {TEST_TOKEN}"},
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
                result = await echo_tool.ainvoke({"message": "Hello FastMCP Auth!"})
                print(f"  authenticated_echo('Hello FastMCP Auth!') = {result}")
            
            # Test get_user_info tool
            user_info_tool = next((t for t in tools if t.name == "get_user_info"), None)
            if user_info_tool:
                result = await user_info_tool.ainvoke({})
                print(f"  get_user_info() = {result}")
            
            # Test secure_add tool
            add_tool = next((t for t in tools if t.name == "secure_add"), None)
            if add_tool:
                result = await add_tool.ainvoke({"a": 10, "b": 5})
                print(f"  secure_add(10, 5) = {result}")
        
        await cleanup()
        print("✅ Valid auth test completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Valid auth test failed: {e}")
        return False

async def test_invalid_authentication():
    """Test invalid token authentication."""
    print("\n❌ Test 2: Invalid JWT Token")
    print("=" * 50)
    
    server_config = {
        "auth-server": {
            "url": "http://127.0.0.1:8001/mcp",
            "headers": {"Authorization": "Bearer invalid-jwt-token-12345"},
            "timeout": 10.0
        }
    }
    
    try:
        tools, cleanup = await convert_mcp_to_langchain_tools(server_config)
        print("❌ This should not succeed!")
        await cleanup()
        return False
        
    except Exception as e:
        print(f"✅ Invalid token correctly rejected: {e}")
        return True

async def test_no_authentication():
    """Test missing authentication header."""
    print("\n🚫 Test 3: No Authentication Header")
    print("=" * 50)
    
    server_config = {
        "auth-server": {
            "url": "http://127.0.0.1:8001/mcp",
            "timeout": 10.0
            # No headers - should fail
        }
    }
    
    try:
        tools, cleanup = await convert_mcp_to_langchain_tools(server_config)
        print("❌ This should not succeed!")
        await cleanup()
        return False
        
    except Exception as e:
        print(f"✅ No auth correctly rejected: {e}")
        return True

async def test_custom_headers():
    """Test custom headers with valid authentication."""
    print("\n🎨 Test 4: Custom Headers with Valid Auth")
    print("=" * 50)
    
    server_config = {
        "custom-auth-server": {
            "url": "http://127.0.0.1:8001/mcp",
            "headers": {
                "Authorization": f"Bearer {TEST_TOKEN}",
                "User-Agent": "langchain-mcp-tools-test-client",
                "X-Custom-Header": "test-value",
                "X-Client-Version": "1.0.0"
            },
            "timeout": 10.0
        }
    }
    
    try:
        tools, cleanup = await convert_mcp_to_langchain_tools(server_config)
        print(f"✅ Connected with custom headers: {len(tools)} tools available")
        await cleanup()
        return True
        
    except Exception as e:
        print(f"❌ Custom headers test failed: {e}")
        return False

async def main():
    """Run all authentication tests."""
    print("🧪 Testing langchain-mcp-tools with FastMCP Bearer Authentication")
    print("=" * 70)
    print("Make sure the FastMCP auth server is running first:")
    print("  • uv run testfiles/streamable_http_bearer_auth_test_server.py")
    print("  • Copy the test token from server output and update TEST_TOKEN in this file")
    print("=" * 70)
    
    if not TEST_TOKEN or TEST_TOKEN.startswith("eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ0ZXN0LWF1dGgtc2VydmVyIiwiYXVkIjoibWNwLXRlc3QtY2xpZW50IiwiaWF0"):
        print("⚠️  WARNING: Please update TEST_TOKEN with the actual token from your server!")
        print("   Look for the line '🔑 Test token: ...' in the server output")
        print("   and paste that token into the TEST_TOKEN variable in this file.")
        return
    
    # Run all tests
    results = []
    results.append(await test_valid_authentication())
    results.append(await test_invalid_authentication())
    results.append(await test_no_authentication())
    results.append(await test_custom_headers())
    
    # Summary
    print("\n🎉 All authentication tests completed!")
    print(f"\n\n📊 Results: {sum(results)}/{len(results)} tests passed\n")
    
    print("\n💡 Summary:")
    print("  ✅ Valid JWT tokens should be accepted")
    print("  ❌ Invalid/missing tokens should be rejected")
    print("  🔧 Tools should work correctly with valid auth")
    print("  🎨 Custom headers should be preserved")
    
    print("\n📋 What this validates:")
    print("  • FastMCP's BearerAuthProvider works correctly")
    print("  • JWT token validation is working")
    print("  • Your library's 'headers' parameter works correctly")
    print("  • Authentication errors are handled properly")

if __name__ == "__main__":
    asyncio.run(main())
