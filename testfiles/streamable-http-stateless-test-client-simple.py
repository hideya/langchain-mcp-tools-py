#!/usr/bin/env python3
"""
Simple Streamable HTTP Stateless Test Client for MCP

This client connects to the simplified server that runs MCP at the root path.
"""

import asyncio
import logging
import sys
from typing import Any

try:
    import httpx
except ImportError as e:
    print(f"\nError: Required package not found: {e}")
    print("Please install required packages: pip install httpx")
    sys.exit(1)

from langchain_mcp_tools import (
    convert_mcp_to_langchain_tools,
    McpServersConfig,
)

# Configuration - Note: using root path instead of /mcp
SERVER_URL = "http://127.0.0.1:3335"
MCP_ENDPOINT = "http://127.0.0.1:3335/"  # Root path
DEBUG = True

class Logger:
    """Enhanced logger with colored output."""
    
    def info(self, *args: Any) -> None:
        print("ℹ️", *args)
    
    def error(self, *args: Any) -> None:
        print("❌", *args)
    
    def debug(self, *args: Any) -> None:
        if DEBUG:
            print("🔍", *args)
    
    def success(self, *args: Any) -> None:
        print("✅", *args)

async def test_simple_connection(logger: Logger) -> bool:
    """Test simple connection to MCP server at root path."""
    logger.info("=== SIMPLE STREAMABLE HTTP TEST ===")
    
    # Check server availability
    try:
        logger.info("Testing server connection...")
        async with httpx.AsyncClient() as client:
            response = await client.get(SERVER_URL, timeout=10.0)
            # We expect this to fail since there's no health check at root
            # But we should get some response indicating MCP is running
        logger.info("Server responded (this might be an MCP protocol response)")
    except Exception as error:
        logger.debug(f"Server response: {error}")
        logger.info("Server seems to be running (expected for MCP-only server)")
    
    try:
        logger.info(f"Connecting to MCP at: {MCP_ENDPOINT}")
        
        # Configure for root path connection
        mcp_servers: McpServersConfig = {
            "simple_server": {
                "url": MCP_ENDPOINT,
                "transport": "streamable_http"
            }
        }
        
        # Convert tools with timeout
        result = await asyncio.wait_for(
            convert_mcp_to_langchain_tools(mcp_servers),
            timeout=30.0
        )
        
        tools, cleanup = result
        
        logger.success("Connection established!")
        logger.info(f"Available tools: {[tool.name for tool in tools]}")
        
        # Test tools
        if tools:
            for tool in tools:
                logger.info(f"Testing {tool.name}...")
                try:
                    if tool.name == "echo":
                        result = await tool._arun(message="Hello from root path!")
                        logger.success(f"{tool.name}: {result}")
                    elif tool.name == "server-info":
                        result = await tool._arun()
                        logger.success(f"{tool.name}: {result}")
                    elif tool.name == "random-number":
                        result = await tool._arun(min_val=1, max_val=10)
                        logger.success(f"{tool.name}: {result}")
                except Exception as e:
                    logger.error(f"Tool {tool.name} failed: {e}")
        
        # Cleanup
        await cleanup()
        logger.success("Test completed successfully!")
        return True
        
    except Exception as error:
        logger.error(f"Test failed: {error}")
        return False

async def main():
    """Main test function."""
    logger = Logger()
    success = await test_simple_connection(logger)
    
    if not success:
        logger.info("\nTroubleshooting:")
        logger.info("1. Make sure the simple server is running:")
        logger.info("   uv run testfiles/streamable-http-stateless-test-server-simple.py")
        logger.info("2. Check that port 3335 is available")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as error:
        print(f"\nUnhandled error: {error}")
        sys.exit(1)
