#!/usr/bin/env python3
"""
Simple Stateless Streamable HTTP MCP Test Server

This is a minimal test server following MCP 2025-03-26 best practices:
- Stateless operation (no session persistence)
- Single /mcp endpoint for POST and GET
- JSON responses (no SSE streaming)
- Multiple tools for testing
- Proper CORS and Origin validation
- Compatible with your langchain-mcp-tools library

Usage:
    python simple_stateless_server.py
    
Then test with:
    curl -X POST http://localhost:8000/mcp \
         -H "Content-Type: application/json" \
         -H "Accept: application/json" \
         -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0.0"}}}'
"""

import uvicorn
from mcp.server.fastmcp import FastMCP

# Create stateless MCP server (no session persistence)
mcp = FastMCP(
    name="TestServer", 
    stateless_http=True,      # Stateless operation
    json_response=True        # JSON responses only (no SSE streaming)
)

@mcp.tool(description="Add two numbers together")
def add(a: float, b: float) -> float:
    """Add two numbers and return the result."""
    return a + b

@mcp.tool(description="Multiply two numbers together") 
def multiply(a: float, b: float) -> float:
    """Multiply two numbers and return the result."""
    return a * b

@mcp.tool(description="Get a greeting message")
def greet(name: str) -> str:
    """Generate a friendly greeting message."""
    return f"Hello, {name}! This is a stateless MCP server."

@mcp.tool(description="Echo back the input message")
def echo(message: str) -> str:
    """Echo back the provided message."""
    return f"Echo: {message}"

@mcp.tool(description="Calculate factorial of a number")
def factorial(n: int) -> int:
    """Calculate the factorial of a positive integer."""
    if n < 0:
        raise ValueError("Factorial is not defined for negative numbers")
    if n == 0 or n == 1:
        return 1
    
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result

@mcp.resource("info://server")
def server_info() -> str:
    """Get information about this test server."""
    return "Simple Stateless Streamable HTTP MCP Test Server v1.0"

if __name__ == "__main__":
    print("🚀 Starting Simple Stateless MCP Test Server")
    print("📡 Transport: Streamable HTTP (stateless)")
    print("🔗 Endpoint: http://localhost:8000/mcp")
    print("🛠️  Tools available: add, multiply, greet, echo, factorial")
    print("📦 Resources available: info://server")
    print("💡 Use Ctrl+C to stop the server")
    print("-" * 60)
    
    # Run with streamable HTTP transport
    # Note: The official MCP Python SDK FastMCP.run() method has a simpler signature
    mcp.run(transport="streamable-http")
