#!/usr/bin/env python3
"""
SSE Authentication Test Client for MCP

This client connects to an MCP server over SSE with JWT authentication.
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

# Import the library
from langchain_mcp_tools import (
    convert_mcp_to_langchain_tools,
    McpServersConfig,
)


# Configure logging
def init_logger() -> logging.Logger:
    """Initialize a simple logger for the client"""
    logging.basicConfig(
        level=logging.INFO,
        format="\x1b[90m%(levelname)s:\x1b[0m %(message)s"
    )
    return logging.getLogger()


# JWT Configuration - must match the server
JWT_SECRET = "MCP_TEST_SECRET"
JWT_ALGORITHM = "HS512"


def create_jwt_token(expiry_minutes=60) -> str:
    """
    Create a JWT token for authenticating with the server.

    Args:
        expiry_minutes: Token expiry time in minutes (default: 60)

    Returns:
        str: JWT token string
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


if __name__ == "__main__":
    print("=== SSE Authentication Test Client ===")
    port = int(os.environ.get("PORT", 9000))
    asyncio.run(run_client(port, init_logger()))
    print("===================================")
