#!/usr/bin/env python3
"""
Test Client for Streamable HTTP MCP Servers

This script tests your langchain-mcp-tools library against the test servers.
It demonstrates both single server and multi-server configurations.

Usage:
    # First start a test server in another terminal:
    python simple_stateless_server.py
    
    # Then run this test client:
    python test_client.py
"""

import asyncio
import logging
from langchain_mcp_tools import convert_mcp_to_langchain_tools

# Configure logging to see the transport detection in action
logging.basicConfig(level=logging.INFO)

async def test_simple_server():
    """Test the simple stateless server."""
    print("🧪 Testing Simple Stateless Server")
    print("=" * 50)
    
    server_config = {
        "test-server": {
            "url": "http://127.0.0.1:8000/mcp",
            # No transport specified - should auto-detect Streamable HTTP
            "timeout": 10.0
        }
    }
    
    try:
        tools, cleanup = await convert_mcp_to_langchain_tools(server_config)
        print(f"✅ Connected to simple server with {len(tools)} tools")
        
        # List available tools
        print("\n🛠️  Available Tools:")
        for tool in tools:
            print(f"  • {tool.name}: {tool.description}")
        
        # Test a few tools
        if tools:
            print("\n🔍 Testing Tools:")
            
            # Test add tool
            add_tool = next((t for t in tools if t.name == "add"), None)
            if add_tool:
                result = await add_tool.ainvoke({"a": 5, "b": 3})
                print(f"  add(5, 3) = {result}")
            
            # Test greet tool
            greet_tool = next((t for t in tools if t.name == "greet"), None)
            if greet_tool:
                result = await greet_tool.ainvoke({"name": "World"})
                print(f"  greet('World') = {result}")
            
            # Test echo tool
            echo_tool = next((t for t in tools if t.name == "echo"), None)
            if echo_tool:
                result = await echo_tool.ainvoke({"message": "Hello MCP!"})
                print(f"  echo('Hello MCP!') = {result}")
        
        await cleanup()
        print("✅ Simple server test completed successfully")
        
    except Exception as e:
        print(f"❌ Error testing simple server: {e}")


async def main():
    """Run all tests."""
    print("🚀 Testing langchain-mcp-tools with Streamable HTTP")
    print("=" * 70)
    print("Make sure you have started the test servers first:")
    print("  • uv run streamable_http_stateless_test_server.py")
    print("=" * 70)
    
    # Test simple server
    await test_simple_server()
    
    print("\n🎉 All tests completed!")
    print("\n💡 Notes:")
    print("  • Transport auto-detection should show 'Streamable HTTP' in logs")
    print("  • No fallback to SSE should occur with these test servers")
    print("  • All servers are stateless (no session persistence)")

if __name__ == "__main__":
    asyncio.run(main())
