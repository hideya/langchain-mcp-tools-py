#!/usr/bin/env python3
"""
SSE Authentication Test Client for MCP

This client demonstrates how to connect to an authenticated MCP SSE server
using the langchain-mcp-tools library. It tests the complete authentication
flow and MCP transport auto-detection.

Key Features:
=============

1. **JWT Authentication**: Generates JWT tokens compatible with the test server
2. **Transport Auto-Detection**: Tests the MCP specification's transport detection
   - First attempts Streamable HTTP (POST InitializeRequest)
   - Falls back to SSE on 4xx errors
3. **Tool Testing**: Demonstrates calling authenticated MCP tools
4. **Error Handling**: Shows proper cleanup and error management

Usage:
======

1. Start the SSE authentication test server:
   uv run testfiles/sse-auth-test-server.py

2. Run this client:
   uv run testfiles/sse-auth-test-client.py

Expected Flow:
==============

1. Client generates JWT token matching server's secret
2. Client tests Streamable HTTP (receives 405 Method Not Allowed)
3. Client falls back to SSE transport
4. Client establishes authenticated SSE connection
5. Client lists and executes tools with authentication
6. Client cleans up connections

Authentication:
===============

The client uses the same JWT configuration as the server:
- Secret: MCP_TEST_SECRET (hardcoded for testing)
- Algorithm: HS512
- Expiry: 60 minutes
- Claims: sub=test-client, iat, exp

For production use:
- Use proper secret management
- Implement token refresh
- Add proper error handling for auth failures
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta

try:
    import jwt
except ImportError as e:
    print(f"\nError: Required package not found: {e}")
    print("Please ensure all required packages are installed\n")
    sys.exit(1)

# Import the langchain-mcp-tools library
from langchain_mcp_tools import (
    convert_mcp_to_langchain_tools,
    McpServersConfig,
)


# Configuration and Setup
# =======================

def init_logger() -> logging.Logger:
    """
    Initialize a simple logger for the client.
    
    Configures logging to show INFO level messages with a clean format
    suitable for monitoring the MCP connection and tool execution.
    
    Returns:
        logging.Logger: Configured logger instance
    """
    logging.basicConfig(
        level=logging.INFO,
        format="\x1b[90m%(levelname)s:\x1b[0m %(message)s"
    )
    return logging.getLogger()


# JWT Configuration - must match the server exactly
JWT_SECRET = "MCP_TEST_SECRET"
JWT_ALGORITHM = "HS512"


def create_jwt_token(expiry_minutes=60) -> str:
    """
    Create a JWT token for authenticating with the MCP server.
    
    This function generates a JWT token with the same configuration as the
    server expects. The token includes standard claims (sub, iat, exp) and
    is signed with the shared secret.
    
    Note: In production, use proper secret management and token refresh patterns.

    Args:
        expiry_minutes: Token expiry time in minutes (default: 60)

    Returns:
        str: JWT token string ready for Authorization header
    """
    expiration = datetime.utcnow() + timedelta(minutes=expiry_minutes)
    payload = {
        "sub": "test-client",
        "exp": expiration,
        "iat": datetime.utcnow(),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


async def run_client(server_port: int, logger: logging.Logger) -> None:
    """
    Run the client that connects to the server with JWT authentication.

    Args:
        server_port: Port where the server is running
        logger: Logger instance
    """
    # Generate JWT token for authentication
    bearer_token = create_jwt_token()
    print("Generated JWT token for authentication")

    # Configure MCP servers with authentication header
    mcp_servers: McpServersConfig = {
        "sse-auth-test-server": {
            "url": f"http://localhost:{server_port}/sse",
            "headers": {"Authorization": f"Bearer {bearer_token}"}
        },
    }

    try:
        # Convert MCP tools to LangChain tools
        print("Connecting to server and converting tools...")
        tools, cleanup = await convert_mcp_to_langchain_tools(
            mcp_servers,
            logger
        )

        print("Successfully connected!"
              f" Available tools: {[tool.name for tool in tools]}")

        # Test each tool directly
        for tool in tools:
            print(f"\nTesting tool: {tool.name}")
            if tool.name == "hello":
                result = await tool._arun(name="Client")
                print(f"Result: {result}")
            elif tool.name == "echo":
                result = await tool._arun(
                    message="This is a test message with authentication"
                )
                print(f"Result: {result}")

        print("\nAll tools tested successfully!")

    finally:
        # Clean up connections
        if 'cleanup' in locals():
            print("Cleaning up connections...")
            await cleanup()


# Entry Point
# ===========

if __name__ == "__main__":
    """
    Main entry point for the test client.
    
    This script can be run directly to test the MCP SSE authentication flow.
    It expects the test server to be running on the specified port (default: 9000).
    
    Environment Variables:
    - PORT: Port where the test server is running (default: 9000)
    
    Expected Output:
    1. JWT token generation message
    2. Connection and transport detection logs
    3. Tool discovery and testing results
    4. Cleanup confirmation
    
    The script demonstrates a complete end-to-end test of:
    - MCP transport auto-detection
    - JWT authentication
    - Tool discovery and execution
    - Proper connection cleanup
    """
    print("=== SSE Authentication Test Client ===")
    port = int(os.environ.get("PORT", 9000))
    asyncio.run(run_client(port, init_logger()))
    print("===================================")
