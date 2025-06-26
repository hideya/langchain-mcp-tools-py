#!/usr/bin/env python3
"""
Test Client for Streamable HTTP MCP Servers

This script tests your langchain-mcp-tools library against the test servers.
It demonstrates both single server and multi-server configurations.

Usage:
    # First start a test server in another terminal:
    python simple_stateless_server.py
    # OR
    python multi_server_fastapi.py
    
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

async def test_multi_server():
    """Test the multi-server FastAPI setup."""
    print("\n🧪 Testing Multi-Server FastAPI Setup")
    print("=" * 50)
    
    multi_server_config = {
        "echo-server": {
            "url": "http://127.0.0.1:8000/echo/mcp",
            "timeout": 10.0
        },
        "math-server": {
            "url": "http://127.0.0.1:8000/math/mcp", 
            "timeout": 10.0
        },
        "utils-server": {
            "url": "http://127.0.0.1:8000/utils/mcp",
            "timeout": 10.0
        }
    }
    
    try:
        tools, cleanup = await convert_mcp_to_langchain_tools(multi_server_config)
        print(f"✅ Connected to multi-server setup with {len(tools)} total tools")
        
        # Group tools by server (based on naming pattern)
        echo_tools = [t for t in tools if t.name in ["echo", "reverse", "uppercase"]]
        math_tools = [t for t in tools if t.name in ["add", "power", "sqrt"]]
        utils_tools = [t for t in tools if t.name in ["generate_uuid", "current_timestamp", "validate_email"]]
        
        print(f"\n📊 Tools Distribution:")
        print(f"  • Echo Server: {len(echo_tools)} tools")
        print(f"  • Math Server: {len(math_tools)} tools") 
        print(f"  • Utils Server: {len(utils_tools)} tools")
        
        # Test tools from each server
        print("\n🔍 Testing Multi-Server Tools:")
        
        # Test echo server
        if echo_tools:
            echo_tool = next((t for t in echo_tools if t.name == "echo"), None)
            if echo_tool:
                result = await echo_tool.ainvoke({"message": "Multi-server test"})
                print(f"  [Echo] echo('Multi-server test') = {result}")
        
        # Test math server
        if math_tools:
            add_tool = next((t for t in math_tools if t.name == "add"), None)
            if add_tool:
                result = await add_tool.ainvoke({"a": 10, "b": 20})
                print(f"  [Math] add(10, 20) = {result}")
        
        # Test utils server
        if utils_tools:
            uuid_tool = next((t for t in utils_tools if t.name == "generate_uuid"), None)
            if uuid_tool:
                result = await uuid_tool.ainvoke({})
                print(f"  [Utils] generate_uuid() = {result}")
            
            email_tool = next((t for t in utils_tools if t.name == "validate_email"), None)
            if email_tool:
                result = await email_tool.ainvoke({"email": "test@example.com"})
                print(f"  [Utils] validate_email('test@example.com') = {result}")
        
        await cleanup()
        print("✅ Multi-server test completed successfully")
        
    except Exception as e:
        print(f"❌ Error testing multi-server: {e}")

async def test_mixed_configuration():
    """Test a mixed configuration with both local and remote servers."""
    print("\n🧪 Testing Mixed Configuration (Local + Remote)")
    print("=" * 60)
    
    mixed_config = {
        # Local stdio server (if you have one available)
        # "filesystem": {
        #     "command": "npx",
        #     "args": ["-y", "@modelcontextprotocol/server-filesystem", "."]
        # },
        
        # Remote streamable HTTP server
        "test-server": {
            "url": "http://127.0.0.1:8000/mcp",
            "timeout": 10.0
        }
    }
    
    try:
        tools, cleanup = await convert_mcp_to_langchain_tools(mixed_config)
        print(f"✅ Connected to mixed configuration with {len(tools)} total tools")
        
        print("\n🛠️  Available Tools from Mixed Config:")
        for tool in tools:
            print(f"  • {tool.name}: {tool.description}")
        
        await cleanup()
        print("✅ Mixed configuration test completed successfully")
        
    except Exception as e:
        print(f"❌ Error testing mixed configuration: {e}")

async def main():
    """Run all tests."""
    print("🚀 Testing langchain-mcp-tools with Streamable HTTP")
    print("=" * 70)
    print("Make sure you have started one of the test servers first:")
    print("  • python simple_stateless_server.py")
    print("  • python multi_server_fastapi.py")
    print("=" * 70)
    
    # Test simple server
    await test_simple_server()
    
    # Test multi-server (comment out if not running multi-server)
    # await test_multi_server()
    
    # Test mixed configuration
    await test_mixed_configuration()
    
    print("\n🎉 All tests completed!")
    print("\n💡 Notes:")
    print("  • Transport auto-detection should show 'Streamable HTTP' in logs")
    print("  • No fallback to SSE should occur with these test servers")
    print("  • All servers are stateless (no session persistence)")

if __name__ == "__main__":
    asyncio.run(main())
