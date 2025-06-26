#!/usr/bin/env python3
"""
Streamable HTTP Stateless Test Server for MCP

This server demonstrates a stateless Streamable HTTP MCP server implementation
using the official MCP Python SDK with FastMCP. In stateless mode, each request
is completely isolated and no session state is maintained.

Key Features:
=============

1. **Stateless Operation**: Uses FastMCP's stateless Streamable HTTP mode
2. **Complete Isolation**: No shared state between requests
3. **Scalability**: Horizontally scalable due to stateless design  
4. **Simplicity**: No session management or authentication complexity

Benefits of Stateless Mode:
==========================

- No session management overhead
- Each request completely isolated
- Concurrent connections work seamlessly
- Simple server implementation
- Fast connection setup
- No memory leaks from accumulated state
- Horizontally scalable

Usage:
======

1. Start this server:
   uv run testfiles/streamable-http-stateless-test-server.py

2. Run the client in another terminal:
   uv run testfiles/streamable-http-stateless-test-client.py

The server exposes these tools:
- echo: Echo a message back
- server-info: Get server information with timestamp
- random-number: Generate random number (demonstrates statelessness)
"""

import asyncio
import random
from datetime import datetime

from mcp.server import FastMCP
import uvicorn
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Mount, Route

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
    print(f"MCP endpoint: http://127.0.0.1:{PORT}/mcp")
    print()
    print("🔧 Stateless Mode Benefits:")
    print("  • No session management required")
    print("  • Each request is completely isolated")
    print("  • Horizontally scalable")
    print("  • Simple deployment")
    print("  • No memory leaks from accumulated state")
    print()

if __name__ == "__main__":
    print_server_info()
    
    try:
        # For stateless StreamableHTTP, run FastMCP app directly
        # Based on GitHub issue #951, mounting causes 307 redirect problems
        # Let's run the MCP app directly at the root with custom routing
        
        # Get the streamable HTTP app from FastMCP
        mcp_app = mcp.streamable_http_app()
        
        # Create a wrapper app that handles both health check and MCP
        from starlette.middleware import Middleware
        from starlette.applications import Starlette
        from starlette.responses import PlainTextResponse
        
        async def app_handler(scope, receive, send):
            """Custom ASGI app that routes requests appropriately."""
            if scope["type"] == "http":
                path = scope["path"]
                method = scope["method"]
                
                debug(f"Received {method} request to {path}")
                
                # Handle health check at root
                if path == "/" and method == "GET":
                    debug("Handling health check")
                    response = PlainTextResponse("MCP Streamable HTTP Stateless Test Server Running")
                    await response(scope, receive, send)
                    return
                
                # Handle MCP requests - route /mcp/* to the MCP app
                elif path.startswith("/mcp"):
                    debug(f"Routing MCP request from {path}")
                    # Adjust the path for the MCP app by removing /mcp prefix
                    new_path = path[4:]  # Remove "/mcp"
                    if not new_path:
                        new_path = "/"
                    
                    debug(f"Adjusted path to: {new_path}")
                    
                    # Create new scope with adjusted path
                    new_scope = {**scope, "path": new_path}
                    await mcp_app(new_scope, receive, send)
                    return
            
            debug(f"Delegating to MCP app: {scope.get('path', 'unknown')}")
            # For all other requests, delegate to MCP app
            await mcp_app(scope, receive, send)
        
        # Run the custom app
        uvicorn.run(app_handler, host="0.0.0.0", port=PORT)
    except KeyboardInterrupt:
        print("\nShutting down stateless server...")
        print("Stateless server stopped")
