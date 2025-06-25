#!/usr/bin/env python3
"""
Streamable HTTP Authentication Test Server for MCP

⚠️ TEST SERVER - NOT OAUTH 2.1 COMPLIANT

This test server implements a simplified authentication mechanism that does NOT
comply with OAuth 2.1 requirements. It's designed solely for testing MCP 
authentication integration with Streamable HTTP transport.

This server demonstrates:
- Basic Bearer token authentication with FastMCP
- Session management for Streamable HTTP
- MCP tool integration with authentication

For production use, implement a proper OAuth 2.1 server with:
- PKCE (Proof Key for Code Exchange) - REQUIRED in OAuth 2.1
- Authorization endpoint with user consent flow
- Token endpoint with proper code exchange
- Authorization Server Metadata (/.well-known/oauth-authorization-server)
- Secure token generation, validation, and refresh
- Dynamic Client Registration (RFC7591) - RECOMMENDED

Key Features:
=============

1. **Session Management**: Maintains active Streamable HTTP sessions
2. **Bearer Token Auth**: Basic token-based authentication
3. **MCP Integration**: Authenticated MCP tools using FastMCP
4. **Token Endpoint**: Simple token issuance for testing

Usage:
======

1. Start this server:
   uv run testfiles/streamable-http-auth-test-server.py

2. Run the auth client:
   uv run testfiles/streamable-http-auth-test-client.py

Authentication Flow:
===================

1. Client requests token from /token endpoint
2. Client includes Bearer token in Authorization header  
3. Server validates token for all MCP requests
4. Server maintains session state for Streamable HTTP
5. Tools require authentication before execution

Note: This implementation uses a simplified approach without the full
OAuth provider interface since it may not be available in all MCP SDK versions.
"""

import uvicorn
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route
from starlette.exceptions import HTTPException

from mcp.server import FastMCP

# Configuration
PORT = 3334
HOST = "0.0.0.0"
DEBUG = True

def debug(*args):
    """Debug logging function."""
    if DEBUG:
        print("[DEBUG]", *args)

# Global variable to store current authentication state
# This pattern allows tools to access auth information
current_auth_token = None

def require_auth():
    """
    Authentication check function for MCP tools.
    
    Raises:
        Exception: If no valid token is present
    """
    global current_auth_token
    if not current_auth_token or not current_auth_token.startswith("test_token_"):
        raise Exception("Authentication required")

# Create FastMCP server
mcp = FastMCP(
    name="MCP Streamable HTTP Auth Test Server",
    description="Authenticated Streamable HTTP test server for MCP"
)

@mcp.tool()
async def echo(message: str) -> str:
    """
    Echo tool that requires authentication.
    
    Args:
        message: Message to echo
        
    Returns:
        str: Echoed message with authentication indicator
    """
    require_auth()  # Verify authentication before proceeding
    debug(f"Got authenticated echo request: {message}")
    return f"[Streamable HTTP] {message}"

@mcp.tool()
async def server_info() -> str:
    """
    Server info tool that requires authentication.
    
    Returns:
        str: Server information with authentication confirmation
    """
    require_auth()  # Verify authentication before proceeding
    debug("Got authenticated server-info request")
    return "MCP Streamable HTTP Auth Test Server - Authentication successful!"

def authenticate_request(request: Request) -> bool:
    """
    Authenticate incoming request using Bearer token.
    
    Args:
        request: Starlette request object
        
    Returns:
        bool: True if authenticated, False otherwise
    """
    global current_auth_token
    
    debug("Authenticating Streamable HTTP request...")
    
    auth_header = request.headers.get("authorization")
    if not auth_header:
        debug("Missing authorization header")
        return False
    
    if not auth_header.startswith("Bearer "):
        debug("Invalid authorization format")
        return False
    
    token = auth_header[7:]  # Remove "Bearer " prefix
    if not token.startswith("test_token_"):
        debug("Invalid token value")
        return False
    
    debug(f"Valid test token: {auth_header}")
    current_auth_token = token
    return True

async def root_handler(request: Request) -> PlainTextResponse:
    """Root endpoint handler."""
    return PlainTextResponse("MCP Streamable HTTP Auth Test Server Running")

async def token_handler(request: Request) -> JSONResponse:
    """
    Basic token endpoint for testing.
    
    ⚠️ This is NOT a proper OAuth 2.1 implementation!
    """
    debug("Token request received")
    
    try:
        body = await request.json()
        client_id = body.get("client_id", "test_client_id")
        
        tokens = {
            "access_token": f"test_token_{client_id}",
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": f"refresh_token_{client_id}"
        }
        
        debug(f"Issuing tokens for client: {client_id}")
        return JSONResponse(content=tokens)
        
    except Exception as error:
        debug(f"Token request error: {error}")
        return JSONResponse(
            status_code=400,
            content={"error": "invalid_request", "error_description": str(error)}
        )

# Custom middleware to handle authentication for MCP endpoints
class AuthMiddleware:
    """Middleware to handle authentication for MCP endpoints."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request = Request(scope, receive)
            
            # Only authenticate MCP endpoints
            if request.url.path.startswith("/mcp"):
                if not authenticate_request(request):
                    response = JSONResponse(
                        status_code=401,
                        content={
                            "jsonrpc": "2.0",
                            "error": {
                                "code": -32000,
                                "message": "Authorization header is required"
                            },
                            "id": None
                        }
                    )
                    await response(scope, receive, send)
                    return
        
        await self.app(scope, receive, send)

# Create the main Starlette application
app = Starlette(routes=[
    Route("/", root_handler, methods=["GET"]),
    Route("/token", token_handler, methods=["POST"]),
])

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=[
        "Content-Type", 
        "Authorization", 
        "Accept", 
        "Mcp-Session-Id", 
        "X-Test-Header"
    ],
)

# Add authentication middleware
app.add_middleware(AuthMiddleware)

# Mount the MCP app
app.mount("/mcp", mcp.streamable_http_app())

def print_server_info():
    """Print server startup information."""
    print(f"\nMCP Streamable HTTP Auth Test Server running at http://{HOST}:{PORT}")
    print(f"For local testing, use: http://127.0.0.1:{PORT}")
    print(f"MCP endpoint: http://127.0.0.1:{PORT}/mcp")
    print(f"Token endpoint: http://127.0.0.1:{PORT}/token")
    print("\n⚠️  TEST SERVER - NOT OAUTH 2.1 COMPLIANT")
    print("This server is for testing MCP authentication integration only.")
    print("For production, implement proper OAuth 2.1 with PKCE.")
    print()

if __name__ == "__main__":
    print_server_info()
    
    try:
        uvicorn.run(app, host=HOST, port=PORT)
    except KeyboardInterrupt:
        print("\nShutting down auth server...")
        print("Auth server stopped")
