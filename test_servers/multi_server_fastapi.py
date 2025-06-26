#!/usr/bin/env python3
"""
Multi-Server FastAPI Streamable HTTP MCP Test Setup

This demonstrates hosting multiple stateless MCP servers in a single FastAPI application.
Follows the official MCP Python SDK best practices for multiple server lifecycle management.

Each server is mounted at a different path:
- /echo/mcp - Simple echo tools
- /math/mcp - Mathematical operations  
- /utils/mcp - Utility functions

Usage:
    python multi_server_fastapi.py
    
Test endpoints:
    http://localhost:8000/echo/mcp
    http://localhost:8000/math/mcp  
    http://localhost:8000/utils/mcp
"""

import contextlib
import uvicorn
from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP

# Create individual MCP servers
echo_mcp = FastMCP(name="EchoServer", stateless_http=True, json_response=True)
math_mcp = FastMCP(name="MathServer", stateless_http=True, json_response=True)
utils_mcp = FastMCP(name="UtilsServer", stateless_http=True, json_response=True)

# Echo Server Tools
@echo_mcp.tool(description="Echo back a message")
def echo(message: str) -> str:
    """Echo back the provided message."""
    return f"Echo: {message}"

@echo_mcp.tool(description="Reverse a string")
def reverse(text: str) -> str:
    """Reverse the characters in a string."""
    return text[::-1]

@echo_mcp.tool(description="Convert text to uppercase")
def uppercase(text: str) -> str:
    """Convert text to uppercase."""
    return text.upper()

# Math Server Tools
@math_mcp.tool(description="Add two numbers")
def add(a: float, b: float) -> float:
    """Add two numbers together."""
    return a + b

@math_mcp.tool(description="Calculate power of a number")
def power(base: float, exponent: float) -> float:
    """Calculate base raised to the power of exponent."""
    return base ** exponent

@math_mcp.tool(description="Calculate square root")
def sqrt(number: float) -> float:
    """Calculate the square root of a number."""
    if number < 0:
        raise ValueError("Cannot calculate square root of negative number")
    return number ** 0.5

# Utils Server Tools
@utils_mcp.tool(description="Generate a UUID")
def generate_uuid() -> str:
    """Generate a random UUID string."""
    import uuid
    return str(uuid.uuid4())

@utils_mcp.tool(description="Get current timestamp")
def current_timestamp() -> str:
    """Get the current timestamp in ISO format."""
    from datetime import datetime
    return datetime.now().isoformat()

@utils_mcp.tool(description="Validate email format")
def validate_email(email: str) -> bool:
    """Validate if the provided string is a valid email format."""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

# Combined lifespan manager for all servers
@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage the lifecycle of all MCP session managers."""
    async with contextlib.AsyncExitStack() as stack:
        await stack.enter_async_context(echo_mcp.session_manager.run())
        await stack.enter_async_context(math_mcp.session_manager.run())
        await stack.enter_async_context(utils_mcp.session_manager.run())
        yield

# Create FastAPI app with lifespan management
app = FastAPI(
    title="Multi-Server MCP Test Setup",
    description="Multiple stateless MCP servers hosted in FastAPI",
    version="1.0.0",
    lifespan=lifespan
)

# Mount each MCP server at different paths
app.mount("/echo", echo_mcp.streamable_http_app())
app.mount("/math", math_mcp.streamable_http_app())
app.mount("/utils", utils_mcp.streamable_http_app())

# Optional: Add a health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "servers": {
            "echo": "http://localhost:8000/echo/mcp",
            "math": "http://localhost:8000/math/mcp", 
            "utils": "http://localhost:8000/utils/mcp"
        }
    }

# Optional: Add a root endpoint with server info
@app.get("/")
async def root():
    """Root endpoint with server information."""
    return {
        "message": "Multi-Server MCP Test Setup",
        "servers": [
            {
                "name": "EchoServer",
                "endpoint": "/echo/mcp",
                "tools": ["echo", "reverse", "uppercase"]
            },
            {
                "name": "MathServer", 
                "endpoint": "/math/mcp",
                "tools": ["add", "power", "sqrt"]
            },
            {
                "name": "UtilsServer",
                "endpoint": "/utils/mcp", 
                "tools": ["generate_uuid", "current_timestamp", "validate_email"]
            }
        ]
    }

if __name__ == "__main__":
    print("🚀 Starting Multi-Server MCP Test Setup")
    print("🔧 FastAPI + Multiple Stateless MCP Servers")
    print("-" * 60)
    print("📡 Echo Server:  http://localhost:8000/echo/mcp")
    print("🧮 Math Server:  http://localhost:8000/math/mcp")
    print("🛠️  Utils Server: http://localhost:8000/utils/mcp")
    print("-" * 60)
    print("🏥 Health Check: http://localhost:8000/health")
    print("📋 Server Info:  http://localhost:8000/")
    print("💡 Use Ctrl+C to stop all servers")
    print("-" * 60)
    
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="info"
    )
