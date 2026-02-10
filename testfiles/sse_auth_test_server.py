#!/usr/bin/env python3
"""
SSE Authentication Test Server for MCP

This server demonstrates the correct pattern for implementing JWT authentication
with FastMCP SSE servers while maintaining compatibility with MCP transport
auto-detection.

Key Architectural Decisions:
==========================

1. **Starlette vs FastAPI**: Uses pure Starlette instead of FastAPI to avoid
   middleware conflicts with FastMCP's SSE streaming implementation. FastAPI's
   middleware stack can interfere with ASGI message types during SSE cleanup.

2. **Transport Detection**: Implements MCP specification requirement that SSE
   servers return 405 Method Not Allowed for POST requests to SSE endpoints
   without session_id to indicate SSE-only transport support.

3. **Authentication Pattern**: Uses global token storage pattern (common in
   community examples) where middleware extracts and stores JWT tokens for
   FastMCP tools to access via require_auth() function.

4. **ASGI Wrapper**: Custom AuthSSEApp class wraps FastMCP's SSE app to handle
   authentication at the ASGI level before passing requests to FastMCP.

Compatibility Notes:
===================

- Compatible with MCP transport auto-detection (Streamable HTTP → SSE fallback)
- Works with FastMCP's session management and tool execution
- Follows community best practices for FastMCP SSE authentication
- Avoids FastAPI middleware assertion errors during connection cleanup

Testing:
========

Use with testfiles/sse_auth_test_client.py to verify:
- Transport auto-detection works (405 → SSE fallback)
- Authentication works for all endpoints
- Tools execute successfully with auth verification
- No server-side errors during connection lifecycle

For production use, consider:
- Proper secret management (not hardcoded JWT secrets)
- Rate limiting and other security measures
- Migration to Streamable HTTP transport (SSE is deprecated)
"""

import os
from datetime import datetime, timedelta

import jwt
import uvicorn
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.exceptions import HTTPException
from mcp.server import FastMCP

# JWT Configuration - for testing only, don't use this in production!
JWT_SECRET = "MCP_TEST_SECRET"
JWT_ALGORITHM = "HS512"
JWT_TOKEN_EXPIRY = 60  # in minutes

# Global variable to store the current request's auth token
# This pattern is commonly used in FastMCP community examples
# and allows tools to access authentication state
auth_token = ""

# Create MCP application using FastMCP
# Note: No port specified here - we'll run with uvicorn directly
mcp = FastMCP("auth-test-mcp")


def create_jwt_token(expiry_minutes=JWT_TOKEN_EXPIRY) -> str:
    """
    Create a JWT token for testing authentication.

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


def verify_jwt(token: str) -> bool:
    """
    Verifies the JWT token.

    Args:
        token: JWT token string

    Returns:
        bool: True if token is valid, False otherwise
    """
    try:
        jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return True
    except jwt.ExpiredSignatureError:
        print("[SERVER] Token expired")
        return False
    except jwt.InvalidTokenError:
        print("[SERVER] Invalid token")
        return False


def require_auth():
    """
    Authentication check function for MCP tools.
    
    This function verifies that the current request has a valid JWT token.
    It's called from individual MCP tools to enforce authentication.
    
    The global token storage pattern allows tools to access authentication
    state without needing to pass tokens through the MCP protocol.
    
    Raises:
        Exception: If no valid token is present
    """
    global auth_token
    if not auth_token or not verify_jwt(auth_token):
        raise Exception("Authentication required")


# MCP Tools Definition
# ===================
# These tools demonstrate how to integrate authentication checks
# with FastMCP tool execution. Each tool calls require_auth() to
# verify the request is authenticated before proceeding.

@mcp.tool()
async def hello(name: str) -> str:
    """
    Simple hello world tool that requires authentication.
    
    Demonstrates the authentication pattern:
    1. Tool is called via MCP protocol
    2. require_auth() checks the global auth token
    3. If valid, tool logic executes
    4. If invalid, tool fails with authentication error

    Args:
        name: Name to greet

    Returns:
        str: Greeting message
    """
    require_auth()  # Verify authentication before proceeding
    print(f"[SERVER] Got hello request from {name}")
    return f"Hello, {name}! Authentication successful."


@mcp.tool()
async def echo(message: str) -> str:
    """
    Echo tool that requires authentication.
    
    Another example of the authentication pattern in MCP tools.

    Args:
        message: Message to echo

    Returns:
        str: Echoed message
    """
    require_auth()  # Verify authentication before proceeding
    print(f"[SERVER] Got echo request: {message}")
    return f"ECHO: {message}"


# Authentication Middleware and ASGI Integration
# ==============================================
# This section implements the authentication layer that wraps FastMCP's
# SSE application while maintaining compatibility with MCP transport detection.

async def auth_middleware(request: Request, call_next):
    """
    Authentication middleware using Starlette patterns.
    
    This middleware handles two critical functions:
    1. MCP transport auto-detection (per MCP specification)
    2. JWT authentication for all SSE endpoints
    
    Transport Detection:
    ------------------
    Per MCP spec, when clients test for Streamable HTTP support by POSTing
    an InitializeRequest to the SSE endpoint, servers should return 405
    Method Not Allowed to indicate they only support SSE transport.
    
    Authentication:
    --------------
    Extracts JWT tokens from Authorization headers and stores them globally
    for FastMCP tools to access. This pattern avoids passing auth through
    the MCP protocol itself.
    
    Args:
        request: Starlette request object
        call_next: Next handler in the chain
    
    Returns:
        Response from FastMCP or auth error response
    """
    global auth_token
    
    # Handle MCP transport detection per specification
    # POST to /sse without session_id = transport detection test
    if (request.method == "POST" and 
        request.url.path == "/sse" and 
        "session_id" not in request.query_params):
        print("[SERVER] POST request to /sse endpoint - returning 405 Method Not Allowed for transport detection")
        return JSONResponse(
            status_code=405,
            content={
                "error": {
                    "code": "method_not_allowed",
                    "message": "This server only supports SSE transport. Use GET for SSE connection."
                }
            },
            headers={"Allow": "GET"}
        )
    
    # Extract and validate JWT token from Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        auth_token = auth_header.split(" ")[1]
        if verify_jwt(auth_token):
            print("[SERVER] Authentication successful")
        else:
            raise HTTPException(status_code=401, detail="Invalid token")
    else:
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    
    # Continue to FastMCP SSE application
    response = await call_next(request)
    return response


# ASGI Application Wrapper
# ========================
# This class wraps FastMCP's SSE application with authentication middleware
# while maintaining proper ASGI patterns that FastMCP expects.

class AuthSSEApp:
    """
    ASGI application wrapper that adds authentication to FastMCP SSE.
    
    This wrapper is necessary because:
    1. We need to authenticate requests before they reach FastMCP
    2. We must maintain ASGI compatibility that FastMCP expects
    3. We want to avoid FastAPI middleware conflicts that cause assertion errors
    
    The wrapper implements the ASGI callable interface and applies
    authentication middleware before delegating to FastMCP's SSE app.
    """
    
    def __init__(self, sse_app):
        """
        Initialize the wrapper with FastMCP's SSE application.
        
        Args:
            sse_app: FastMCP's SSE ASGI application
        """
        self.sse_app = sse_app
    
    async def __call__(self, scope, receive, send):
        """
        ASGI callable that handles authentication then delegates to FastMCP.
        
        This method:
        1. Creates a Starlette Request from ASGI scope
        2. Applies authentication middleware
        3. Delegates to FastMCP's SSE app if auth succeeds
        4. Returns auth errors if auth fails
        
        Args:
            scope: ASGI scope dict
            receive: ASGI receive callable
            send: ASGI send callable
        """
        # Create request object for middleware
        request = Request(scope, receive)
        
        async def call_next(request):
            # Delegate to FastMCP's SSE application
            return await self.sse_app(scope, receive, send)
        
        try:
            # Apply authentication middleware
            result = await auth_middleware(request, call_next)
            # If middleware returns a response object, send it
            if hasattr(result, '__call__'):
                await result(scope, receive, send)
            return result
        except HTTPException as e:
            # Handle authentication errors
            response = JSONResponse(
                status_code=e.status_code,
                content={"error": e.detail}
            )
            await response(scope, receive, send)


# Application Setup
# =================
# Final assembly of the Starlette application with authenticated FastMCP SSE routes.

# Get FastMCP's SSE ASGI application
sse_app = mcp.sse_app()

# Create authenticated wrapper
auth_sse_app = AuthSSEApp(sse_app)

# Define routes for MCP SSE endpoints
# Both /sse and /messages/ need to go through the same auth wrapper
routes = [
    Route("/sse", auth_sse_app, methods=["GET", "POST"]),
    Route("/messages/", auth_sse_app, methods=["POST"]),
]

# Create the main Starlette application
# This is what uvicorn will serve
app = Starlette(routes=routes)


def print_token_info():
    """
    Print token information to help with testing.
    
    Generates a sample JWT token and displays connection information
    for easy testing with the companion test client.
    """
    token = create_jwt_token()
    print("\n=== SSE Authentication Test Server ===")
    print(f"JWT Secret: {JWT_SECRET}")
    print(f"JWT Algorithm: {JWT_ALGORITHM}")
    print(f"JWT Expiry: {JWT_TOKEN_EXPIRY} minutes")
    print("\nSample Token for Testing:")
    print(f"Bearer {token}")
    print("\nConnect using:")
    print("http://localhost:9000/sse")
    print("=====================================\n")


if __name__ == "__main__":
    # Print helpful information for testing
    port = int(os.environ.get("PORT", 9000))
    print_token_info()
    
    # Run with uvicorn
    # Note: We use the Starlette app directly, not FastMCP's built-in server
    uvicorn.run(app, host="0.0.0.0", port=port)
