#!/usr/bin/env python3
"""
Simple OAuth MCP Test Server

This server implements a minimal OAuth 2.0 authorization server for testing
your langchain-mcp-tools library's auth parameter support.

This is a simplified version that focuses on testing the OAuth flow
rather than implementing a production-ready OAuth server.

Usage:
    python simple_oauth_server.py
    
Test with:
    python test_oauth_client.py
"""

import secrets
import time
import uvicorn
from typing import Any, Dict
from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from urllib.parse import urlencode, parse_qs
from mcp.server.fastmcp import FastMCP

# In-memory storage for simplicity (production would use a database)
clients: Dict[str, Dict[str, Any]] = {}
authorization_codes: Dict[str, Dict[str, Any]] = {}
access_tokens: Dict[str, Dict[str, Any]] = {}

# Pre-register a test client
TEST_CLIENT = {
    "client_id": "test-mcp-client-123",
    "client_secret": "secret-456", 
    "redirect_uris": ["http://localhost:3000/callback"],
    "grant_types": ["authorization_code", "refresh_token"],
    "response_types": ["code"],
    "scopes": ["read", "write"]
}
clients[TEST_CLIENT["client_id"]] = TEST_CLIENT

# Create FastAPI app
app = FastAPI(title="Simple OAuth MCP Test Server")

# Create MCP server (stateless) 
mcp = FastMCP(
    name="OAuthTestServer",
    stateless_http=True,
    json_response=True
)

@mcp.tool(description="Get authenticated user information")
def get_current_user() -> str:
    """Get information about the currently authenticated user."""
    return "Authenticated user: test-user@example.com (OAuth verified)"

@mcp.tool(description="List user's documents")
def list_user_documents() -> str:
    """List documents accessible to the authenticated user."""
    return "User documents: document1.pdf, document2.txt, report.xlsx (OAuth authenticated)"

@mcp.tool(description="Create a new document")
def create_document(title: str, content: str) -> str:
    """Create a new document for the authenticated user."""
    return f"Created document '{title}' with content: {content[:50]}... (OAuth authenticated)"

@mcp.resource("user://profile")
def get_user_profile() -> str:
    """Get user profile information."""
    return "User profile: John Doe, john@example.com, Premium Account (OAuth authenticated)"

# OAuth Authorization Server Endpoints

@app.get("/.well-known/oauth-authorization-server")
async def authorization_server_metadata():
    """OAuth 2.0 Authorization Server Metadata (RFC 8414)."""
    return {
        "issuer": "http://localhost:8003",
        "authorization_endpoint": "http://localhost:8003/authorize",
        "token_endpoint": "http://localhost:8003/token",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "code_challenge_methods_supported": ["S256"],
        "scopes_supported": ["read", "write"],
        "token_endpoint_auth_methods_supported": ["client_secret_post"]
    }

@app.get("/authorize")
async def authorize(
    response_type: str,
    client_id: str, 
    redirect_uri: str,
    scope: str = "",
    state: str = "",
    code_challenge: str = "",
    code_challenge_method: str = ""
):
    """OAuth authorization endpoint."""
    # Validate client
    client = clients.get(client_id)
    if not client:
        raise HTTPException(status_code=400, detail="Invalid client_id")
    
    # Validate redirect URI
    if redirect_uri not in client["redirect_uris"]:
        raise HTTPException(status_code=400, detail="Invalid redirect_uri")
    
    # For testing, auto-approve the authorization
    # In production, this would show a consent screen
    auth_code = f"code_{secrets.token_hex(16)}"
    
    # Store authorization code
    authorization_codes[auth_code] = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
        "expires_at": time.time() + 600,  # 10 minutes
        "used": False
    }
    
    # Redirect back to client with code
    params = {"code": auth_code}
    if state:
        params["state"] = state
    
    redirect_url = f"{redirect_uri}?{urlencode(params)}"
    return RedirectResponse(url=redirect_url)

@app.post("/token")
async def token_endpoint(
    grant_type: str = Form(...),
    client_id: str = Form(...),
    client_secret: str = Form(...),
    code: str = Form(None),
    redirect_uri: str = Form(None),
    code_verifier: str = Form(None)
):
    """OAuth token endpoint."""
    # Validate client credentials
    client = clients.get(client_id)
    if not client or client["client_secret"] != client_secret:
        raise HTTPException(status_code=401, detail="Invalid client credentials")
    
    if grant_type == "authorization_code":
        # Validate authorization code
        auth_code_data = authorization_codes.get(code)
        if not auth_code_data:
            raise HTTPException(status_code=400, detail="Invalid authorization code")
        
        if auth_code_data["used"]:
            raise HTTPException(status_code=400, detail="Authorization code already used")
        
        if auth_code_data["expires_at"] < time.time():
            raise HTTPException(status_code=400, detail="Authorization code expired")
        
        if auth_code_data["client_id"] != client_id:
            raise HTTPException(status_code=400, detail="Client mismatch")
        
        # Mark code as used
        auth_code_data["used"] = True
        
        # Generate access token
        access_token = f"token_{secrets.token_hex(32)}"
        refresh_token = f"refresh_{secrets.token_hex(32)}"
        
        # Store tokens
        access_tokens[access_token] = {
            "client_id": client_id,
            "scope": auth_code_data["scope"],
            "expires_at": time.time() + 3600,  # 1 hour
            "token_type": "Bearer"
        }
        
        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": refresh_token,
            "scope": auth_code_data["scope"]
        }
    
    else:
        raise HTTPException(status_code=400, detail="Unsupported grant type")

# Authentication middleware for MCP endpoints
@app.middleware("http")
async def oauth_auth_middleware(request: Request, call_next):
    """Apply OAuth authentication to MCP endpoints."""
    if request.url.path.startswith("/mcp"):
        # Check for Authorization header
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"error": "invalid_token", "error_description": "Missing or invalid access token"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Extract and validate token
        token = auth_header.replace("Bearer ", "")
        token_data = access_tokens.get(token)
        if not token_data:
            return JSONResponse(
                status_code=401,
                content={"error": "invalid_token", "error_description": "Invalid access token"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check if token expired
        if token_data["expires_at"] < time.time():
            return JSONResponse(
                status_code=401,
                content={"error": "invalid_token", "error_description": "Access token expired"},
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    response = await call_next(request)
    return response

# Mount the MCP app
app.mount("/mcp", mcp.streamable_http_app())

# Info endpoints
@app.get("/")
async def root():
    """Server information."""
    return {
        "name": "Simple OAuth MCP Test Server",
        "oauth_endpoints": {
            "authorization": "/authorize",
            "token": "/token",
            "metadata": "/.well-known/oauth-authorization-server"
        },
        "mcp_endpoint": "/mcp",
        "test_client": {
            "client_id": TEST_CLIENT["client_id"],
            "client_secret": TEST_CLIENT["client_secret"],
            "redirect_uris": TEST_CLIENT["redirect_uris"]
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "auth": "oauth2"}

if __name__ == "__main__":
    print("🚀 Starting Simple OAuth MCP Test Server")
    print("🔐 Authentication: OAuth 2.0")
    print("🔗 MCP Endpoint: http://localhost:8003/mcp")
    print("🔑 OAuth Endpoints:")
    print("  • Authorization: http://localhost:8003/authorize")
    print("  • Token: http://localhost:8003/token")
    print("  • Metadata: http://localhost:8003/.well-known/oauth-authorization-server")
    print("-" * 70)
    print("🧪 Test Client Credentials:")
    print(f"  • Client ID: {TEST_CLIENT['client_id']}")
    print(f"  • Client Secret: {TEST_CLIENT['client_secret']}")
    print(f"  • Redirect URI: {TEST_CLIENT['redirect_uris'][0]}")
    print("-" * 70)
    print("🛠️  Tools available: get_current_user, list_user_documents, create_document")
    print("📦 Resources available: user://profile")
    print("💡 Use Ctrl+C to stop the server")
    print("-" * 70)
    
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8003,
        log_level="info"
    )
