#!/usr/bin/env python3
"""
Streamable HTTP Stateless Test Client for MCP

This client demonstrates how to connect to a stateless Streamable HTTP MCP server
using the langchain-mcp-tools library. It tests various connection patterns and
demonstrates the benefits of stateless operation.

Key Features:
=============

1. **Stateless Connection**: Tests stateless Streamable HTTP transport
2. **Auto-Detection**: Tests transport auto-detection (should use Streamable HTTP)
3. **Concurrent Connections**: Demonstrates stateless scalability
4. **Tool Testing**: Tests all available tools
5. **Error Handling**: Proper cleanup and error management

Benefits of Stateless Mode:
==========================

- No authentication complexity
- No session management overhead
- Each request completely isolated
- Concurrent connections work seamlessly
- Simple server implementation
- Fast connection setup

Usage:
======

1. Start the stateless test server:
   uv run testfiles/streamable-http-stateless-test-server.py

2. Run this client:
   uv run testfiles/streamable-http-stateless-test-client.py

Expected Flow:
==============

1. Client checks if server is running
2. Client tests explicit Streamable HTTP connection
3. Client tests transport auto-detection
4. Client demonstrates concurrent connections
5. Client cleans up all connections

The client will test these tools:
- echo: Simple message echo
- server-info: Get server information with timestamp
- random-number: Generate random numbers (shows statelessness)
"""

import asyncio
import logging
import os
import sys
from typing import Any, List, Tuple

try:
    import httpx
except ImportError as e:
    print(f"\nError: Required package not found: {e}")
    print("Please install required packages: pip install httpx")
    sys.exit(1)

# Import the langchain-mcp-tools library
from langchain_mcp_tools import (
    convert_mcp_to_langchain_tools,
    McpServersConfig,
)

# Configuration
SERVER_URL = "http://127.0.0.1:3335"
DEBUG = True

# Enhanced logging
class Logger:
    """Enhanced logger with colored output."""
    
    def info(self, *args: Any) -> None:
        print("ℹ️", *args)
    
    def warn(self, *args: Any) -> None:
        print("⚠️", *args)
    
    def error(self, *args: Any) -> None:
        print("❌", *args)
    
    def debug(self, *args: Any) -> None:
        if DEBUG:
            print("🔍", *args)
    
    def success(self, *args: Any) -> None:
        print("✅", *args)


async def check_server_availability(logger: Logger) -> bool:
    """
    Check if the server is running and available.
    
    Args:
        logger: Logger instance
        
    Returns:
        bool: True if server is available, False otherwise
    """
    try:
        logger.info("Testing server connection...")
        async with httpx.AsyncClient() as client:
            response = await client.get(SERVER_URL, timeout=10.0)
            if response.status_code != 200:
                raise httpx.HTTPStatusError(
                    f"Server error: {response.status_code}",
                    request=response.request,
                    response=response
                )
        logger.success("Stateless server is running")
        return True
    except Exception as error:
        logger.error(f"Server unavailable: {error}")
        logger.info("Make sure to start the server with: uv run testfiles/streamable-http-stateless-test-server.py")
        return False


async def test_explicit_stateless_connection(logger: Logger) -> bool:
    """
    Test explicit stateless Streamable HTTP connection.
    
    Args:
        logger: Logger instance
        
    Returns:
        bool: True if test passed, False otherwise
    """
    logger.info("\n--- Testing Explicit Stateless Streamable HTTP ---")
    
    try:
        # Create timeout for connection
        timeout = 30.0
        
        logger.info(f"Using URL: {SERVER_URL}/mcp")
        logger.info("Using transport: Streamable HTTP (stateless mode)")
        logger.info("Authentication: None required")
        
        # Configure MCP servers for explicit stateless connection
        mcp_servers: McpServersConfig = {
            "stateless_server": {
                "url": f"{SERVER_URL}/mcp",
                "transport": "streamable_http"  # Explicit transport
                # No auth options needed for stateless
            }
        }
        
        # Convert tools with timeout
        result = await asyncio.wait_for(
            convert_mcp_to_langchain_tools(mcp_servers),
            timeout=timeout
        )
        
        tools, cleanup = result
        
        logger.success("Stateless connection established!")
        logger.info(f"Available tools: {[tool.name for tool in tools]}")
        
        # Test available tools
        if tools:
            echo_tool = next((t for t in tools if t.name == "echo"), None)
            info_tool = next((t for t in tools if t.name == "server-info"), None)
            random_tool = next((t for t in tools if t.name == "random-number"), None)
            
            if echo_tool:
                logger.info("Testing echo tool...")
                result = await echo_tool._arun(message="Hello from stateless server!")
                logger.success(f"Echo tool result: {result}")
            
            if info_tool:
                logger.info("Testing server-info tool...")
                result = await info_tool._arun()
                logger.success(f"Server-info result: {result}")
            
            if random_tool:
                logger.info("Testing random-number tool...")
                result1 = await random_tool._arun(min_val=1, max_val=10)
                logger.success(f"Random number result 1: {result1}")
                
                # Test again to show statelessness
                result2 = await random_tool._arun(min_val=100, max_val=200)
                logger.success(f"Random number result 2: {result2}")
        
        # Clean up connection
        await cleanup()
        logger.success("Explicit connection cleaned up")
        return True
        
    except asyncio.TimeoutError:
        logger.error("Connection timeout (30s)")
        return False
    except Exception as error:
        logger.error(f"Test failed: {error}")
        return False


async def test_auto_detection_connection(logger: Logger) -> bool:
    """
    Test auto-detection connection (should use Streamable HTTP).
    
    Args:
        logger: Logger instance
        
    Returns:
        bool: True if test passed, False otherwise
    """
    logger.info("\n--- Testing Auto-Detection (should use Streamable HTTP) ---")
    
    try:
        # Create timeout for connection
        timeout = 30.0
        
        # Configure MCP servers for auto-detection
        mcp_servers: McpServersConfig = {
            "auto_stateless_server": {
                "url": f"{SERVER_URL}/mcp"
                # No transport specified - should auto-detect Streamable HTTP
                # No auth options needed
            }
        }
        
        # Convert tools with timeout
        result = await asyncio.wait_for(
            convert_mcp_to_langchain_tools(mcp_servers),
            timeout=timeout
        )
        
        tools, cleanup = result
        
        logger.success("Auto-detection connection established!")
        logger.info(f"Available tools: {[tool.name for tool in tools]}")
        
        # Test tools with auto-detection
        if tools:
            echo_tool = next((t for t in tools if t.name == "echo"), None)
            if echo_tool:
                logger.info("Testing echo tool with auto-detection...")
                result = await echo_tool._arun(message="Hello from auto-detected stateless server!")
                logger.success(f"Auto-detection echo result: {result}")
        
        # Clean up connection
        await cleanup()
        logger.success("Auto-detection connection cleaned up")
        return True
        
    except asyncio.TimeoutError:
        logger.error("Connection timeout (30s)")
        return False
    except Exception as error:
        logger.error(f"Test failed: {error}")
        return False


async def test_concurrent_connections(logger: Logger) -> bool:
    """
    Test multiple concurrent connections to demonstrate stateless benefits.
    
    Args:
        logger: Logger instance
        
    Returns:
        bool: True if test passed, False otherwise
    """
    logger.info("\n--- Testing Concurrent Connections (Stateless Advantage) ---")
    logger.info("Making 3 concurrent connections to demonstrate stateless scalability...")
    
    try:
        async def create_concurrent_connection(index: int) -> str:
            """Create a single concurrent connection and test it."""
            mcp_servers: McpServersConfig = {
                f"concurrent_{index}": {
                    "url": f"{SERVER_URL}/mcp",
                    "transport": "streamable_http"
                }
            }
            
            tools, cleanup = await convert_mcp_to_langchain_tools(mcp_servers)
            
            # Test a tool from this connection
            echo_tool = next((t for t in tools if t.name == "echo"), None)
            tool_result = "No echo tool found"
            if echo_tool:
                tool_result = await echo_tool._arun(message=f"Concurrent request #{index + 1}")
                logger.success(f"Concurrent {index + 1} result: {tool_result}")
            
            await cleanup()
            return f"Connection {index + 1} completed"
        
        # Create 3 concurrent connections
        concurrent_tasks = [
            create_concurrent_connection(i) for i in range(3)
        ]
        
        # Wait for all to complete
        results = await asyncio.gather(*concurrent_tasks)
        logger.success(f"All concurrent connections completed: {results}")
        
        return True
        
    except Exception as error:
        logger.error(f"Concurrent test failed: {error}")
        return False


async def main() -> None:
    """Main test function."""
    logger = Logger()
    logger.info("=== MCP STREAMABLE HTTP STATELESS TEST ===")
    
    # Check server availability
    if not await check_server_availability(logger):
        return
    
    # Run tests
    tests_passed = 0
    total_tests = 3
    
    # Test explicit stateless connection
    if await test_explicit_stateless_connection(logger):
        tests_passed += 1
    
    # Small delay between tests
    await asyncio.sleep(1)
    
    # Test auto-detection
    if await test_auto_detection_connection(logger):
        tests_passed += 1
    
    # Small delay between tests
    await asyncio.sleep(1)
    
    # Test concurrent connections
    if await test_concurrent_connections(logger):
        tests_passed += 1
    
    # Print results
    if tests_passed == total_tests:
        logger.success("\n🎉 All stateless Streamable HTTP tests completed successfully!")
        
        logger.info("\n📋 Stateless Benefits Demonstrated:")
        logger.info("  ✅ No authentication complexity")
        logger.info("  ✅ No session management overhead")
        logger.info("  ✅ Each request completely isolated")
        logger.info("  ✅ Concurrent connections work seamlessly")
        logger.info("  ✅ Simple server implementation")
        logger.info("  ✅ Fast connection setup")
    else:
        logger.error(f"\n❌ {total_tests - tests_passed} out of {total_tests} tests failed")
        
        logger.info("\nTroubleshooting tips:")
        logger.info(f"1. Make sure the stateless server is running at: {SERVER_URL}")
        logger.info("2. Start server: uv run testfiles/streamable-http-stateless-test-server.py")
        logger.info("3. Check network connectivity and firewall settings")
        logger.info("4. Verify no authentication is required (stateless mode)")
        logger.info("5. Ensure the server port 3335 is available")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as error:
        print(f"\nUnhandled error: {error}")
        sys.exit(1)
