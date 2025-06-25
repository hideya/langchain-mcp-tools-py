#!/usr/bin/env python3
"""
Streamable HTTP Stateless Test Server for MCP (Simplified Version)

This version runs the FastMCP streamable HTTP app directly at the root path
to avoid any mounting/routing issues that cause 307 redirects or 404 errors.

This approach sacrifices the health check endpoint for simplicity and
better compatibility with the MCP SDK.
"""

import asyncio
import random
from datetime import datetime

from mcp.server import FastMCP

# Configuration
PORT = 3335
DEBUG = True

def debug(*args):
    """Debug logging function."""
    if DEBUG:
        print("[DEBUG]", *args)

# Create FastMCP server in stateless mode
mcp = FastMCP(
    name="MCP Streamable HTTP Stateless Test Server",
    description="Stateless Streamable HTTP test server for MCP",
    # Enable stateless HTTP mode - key for stateless operation
    stateless_http=True
)

@mcp.tool()
async def echo(message: str) -> str:
    """Echo a message back with stateless indicator."""
    debug(f"Echo tool called with message: {message}")
    return f"[Stateless Streamable HTTP] {message}"

@mcp.tool()
async def server_info() -> str:
    """Get server information with current timestamp."""
    debug("Server info tool called")
    timestamp = datetime.now().isoformat()
    return f"MCP Streamable HTTP Stateless Test Server - Request handled at {timestamp}"

@mcp.tool()
async def random_number(min_val: int = 1, max_val: int = 100) -> str:
    """Generate a random number to demonstrate statelessness."""
    debug(f"Random number tool called with range {min_val}-{max_val}")
    random_num = random.randint(min_val, max_val)
    return f"Random number between {min_val} and {max_val}: {random_num}"

def print_server_info():
    """Print server startup information."""
    print(f"\nMCP Streamable HTTP Stateless Test Server running on port {PORT}")
    print(f"For local testing, use: http://127.0.0.1:{PORT}")
    print(f"MCP endpoint: http://127.0.0.1:{PORT}/")  # Note: root path
    print()
    print("🔧 Stateless Mode Benefits:")
    print("  • No session management required")
    print("  • Each request is completely isolated")
    print("  • Horizontally scalable")
    print("  • Simple deployment")
    print("  • No memory leaks from accumulated state")
    print()
    print("Note: This version runs MCP directly at root path to avoid routing issues")

if __name__ == "__main__":
    print_server_info()
    
    try:
        # Run FastMCP streamable HTTP app directly at root
        # This is the simplest approach that should work without routing issues
        import uvicorn
        mcp_app = mcp.streamable_http_app()
        uvicorn.run(mcp_app, host="0.0.0.0", port=PORT)
    except KeyboardInterrupt:
        print("\nShutting down stateless server...")
        print("Stateless server stopped")
