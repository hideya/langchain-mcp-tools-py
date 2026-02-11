#!/usr/bin/env python3
"""
Simple Stateless Streamable HTTP Test Server (No Authentication)
 
A minimal FastMCP server for testing Streamable HTTP transport
with langchain-mcp-tools.
"""
 
from fastmcp import FastMCP
 
# Create FastMCP server (no auth)
mcp = FastMCP(name="StatelessTestServer")
 
@mcp.tool(description="Add two numbers")
def add(a: float, b: float) -> float:
    """Add two numbers together."""
    return a + b
 
@mcp.tool(description="Greet someone by name")
def greet(name: str) -> str:
    """Return a greeting message."""
    return f"Hello, {name}!"
 
@mcp.tool(description="Echo back a message")
def echo(message: str) -> str:
    """Echo back the input message."""
    return f"Echo: {message}"
 
if __name__ == "__main__":
    print("🚀 Starting Simple Stateless Streamable HTTP Test Server")
    print("🔗 Endpoint: http://127.0.0.1:8002/mcp")
    print("🛠️  Tools available: add, greet, echo")
    print("-" * 70)
    print("💡 Use Ctrl+C to stop the server")
 
    mcp.run(
        transport="http",
        host="127.0.0.1",
        port=8002,
        path="/mcp"
    )
