#!/usr/bin/env python3
"""
Simple Bearer Token Authentication MCP Test Server

This server demonstrates basic bearer token authentication for testing your
langchain-mcp-tools library's authentication support.

Features:
- Simple bearer token validation  
- Multiple authentication scenarios
- Clear error messages for debugging
- Streamable HTTP transport

Usage:
    python simple_bearer_auth_server.py
    
Test with:
    curl -H "Authorization: Bearer valid-token-123" http://localhost:8001/mcp
"""

import uvicorn
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from mcp.server.fastmcp import FastMCP

# Valid tokens for testing (in production, validate against a real auth system)
VALID_TOKENS = {
    "valid-token-123": {"user": "alice", "scopes": ["read", "write"]},
    "read-only-token": {"user": "bob", "scopes": ["read"]},
    "expired-token": {"user": "charlie", "scopes": [], "status": "expired"},
    "test-token-789": {"user": "test-user", "scopes": ["read", "write", "admin"]},
}

# Create FastAPI app for custom authentication middleware
app = FastAPI(title="MCP Bearer Auth Test Server")
security = HTTPBearer()

# Create MCP server (stateless)
mcp = FastMCP(
    name="BearerAuthTestServer",
    stateless_http=True,
    json_response=True
)

def validate_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Validate bearer token and return user info."""
    token = credentials.credentials
    
    if token not in VALID_TOKENS:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token_data = VALID_TOKENS[token]
    
    # Check for expired tokens
    if token_data.get("status") == "expired":
        raise HTTPException(
            status_code=401,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return token_data

@mcp.tool(description="Echo back text with user information")
def authenticated_echo(message: str) -> str:
    """Echo back a message with authentication context."""
    # In a real server, you'd get user context from the request
    # For testing, we'll just echo the message
    return f"Authenticated echo: {message}"

@mcp.tool(description="Get current user information")  
def get_user_info() -> str:
    """Get information about the authenticated user."""
    # This would normally access the authenticated user context
    return "User info: authenticated user (token validation successful)"

@mcp.tool(description="Admin-only operation")
def admin_operation(action: str) -> str:
    """Perform an admin operation (requires admin scope)."""
    return f"Admin operation executed: {action}"

@mcp.tool(description="Add two numbers (requires authentication)")
def secure_add(a: float, b: float) -> float:
    """Add two numbers securely."""
    return a + b

@mcp.resource("user://profile")
def get_user_profile() -> str:
    """Get user profile information."""
    return "User profile: authenticated user profile data"

# Mount MCP app with authentication middleware
@app.middleware("http")
async def auth_middleware(request, call_next):
    """Apply authentication to MCP endpoints."""
    if request.url.path.startswith("/mcp"):
        # Check for Authorization header
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=401,
                content={"error": "Missing or invalid Authorization header"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Extract and validate token
        token = auth_header.replace("Bearer ", "")
        if token not in VALID_TOKENS:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=401,
                content={"error": "Invalid authentication token"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        token_data = VALID_TOKENS[token]
        if token_data.get("status") == "expired":
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=401,
                content={"error": "Token has expired"},
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    response = await call_next(request)
    return response

# Mount the MCP app
app.mount("/mcp", mcp.streamable_http_app())

# Health check endpoint (no auth required)
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "auth": "bearer-token"}

# Auth info endpoint (no auth required) 
@app.get("/auth-info")
async def auth_info():
    """Get authentication information for testing."""
    return {
        "auth_type": "bearer",
        "endpoint": "/mcp",
        "valid_tokens": list(VALID_TOKENS.keys()),
        "example_header": "Authorization: Bearer valid-token-123",
        "test_tokens": {
            "valid-token-123": "Full access",
            "read-only-token": "Read-only access",
            "expired-token": "Expired token (will fail)",
            "test-token-789": "Test user with admin access"
        }
    }

if __name__ == "__main__":
    print("🚀 Starting Bearer Token Authentication MCP Test Server")
    print("🔐 Authentication: Bearer Token")
    print("🔗 Endpoint: http://localhost:8001/mcp")
    print("🛠️  Tools available: authenticated_echo, get_user_info, admin_operation, secure_add")
    print("📦 Resources available: user://profile")
    print("-" * 70)
    print("🔑 Valid test tokens:")
    for token, data in VALID_TOKENS.items():
        status = f" ({data.get('status', 'active')})" if data.get('status') else ""
        print(f"  • {token}: {data['user']}{status}")
    print("-" * 70)
    print("🧪 Test commands:")
    print("  # Valid request:")
    print('  curl -H "Authorization: Bearer valid-token-123" http://localhost:8001/mcp')
    print("  # Invalid request (should fail):")
    print('  curl http://localhost:8001/mcp')
    print("  # Auth info:")
    print('  curl http://localhost:8001/auth-info')
    print("-" * 70)
    print("💡 Use Ctrl+C to stop the server")
    
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8001,
        log_level="info"
    )
