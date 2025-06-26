#!/usr/bin/env python3
"""
API Key Authentication MCP Test Server

This server demonstrates API key authentication for testing your
langchain-mcp-tools library's authentication support.

Different from bearer tokens, this uses custom API key headers
which is a common pattern for many APIs.

Features:
- X-API-Key header authentication
- Multiple API key scenarios
- Rate limiting simulation
- Clear error messages

Usage:
    python api_key_auth_server.py
    
Test with:
    curl -H "X-API-Key: sk-test-key-123" http://localhost:8002/mcp
"""

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from mcp.server.fastmcp import FastMCP

# Valid API keys for testing
VALID_API_KEYS = {
    "sk-test-key-123": {"user": "alice", "plan": "pro", "requests_left": 1000},
    "sk-demo-key-456": {"user": "demo", "plan": "free", "requests_left": 10},
    "sk-admin-key-789": {"user": "admin", "plan": "enterprise", "requests_left": float('inf')},
    "sk-expired-key": {"user": "expired", "plan": "free", "requests_left": 0, "status": "expired"},
    "sk-limited-key": {"user": "limited", "plan": "basic", "requests_left": 1},
}

# Create FastAPI app
app = FastAPI(title="MCP API Key Auth Test Server")

# Create MCP server (stateless)
mcp = FastMCP(
    name="ApiKeyAuthTestServer",
    stateless_http=True,
    json_response=True
)

@mcp.tool(description="Get weather information")
def get_weather(city: str) -> str:
    """Get weather information for a city."""
    return f"Weather in {city}: Sunny, 22°C (API key authenticated)"

@mcp.tool(description="Send a notification")
def send_notification(message: str, recipient: str) -> str:
    """Send a notification to a recipient."""
    return f"Notification sent to {recipient}: {message} (API key authenticated)"

@mcp.tool(description="List user documents")
def list_documents() -> str:
    """List documents accessible to the authenticated user."""
    return "Documents: doc1.txt, doc2.pdf, report.xlsx (API key authenticated)"

@mcp.tool(description="Premium feature - AI analysis")
def ai_analysis(data: str) -> str:
    """Perform AI analysis on data (premium feature)."""
    return f"AI Analysis Result: {data} processed successfully (premium API key required)"

@mcp.resource("api://usage")
def get_api_usage() -> str:
    """Get API usage statistics."""
    return "API Usage: 150/1000 requests this month (API key authenticated)"

# Authentication middleware
@app.middleware("http")
async def api_key_auth_middleware(request: Request, call_next):
    """Apply API key authentication to MCP endpoints."""
    if request.url.path.startswith("/mcp"):
        # Check for X-API-Key header
        api_key = request.headers.get("x-api-key")
        if not api_key:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=401,
                content={
                    "error": "Missing API key",
                    "message": "Please provide an X-API-Key header",
                    "code": "MISSING_API_KEY"
                },
                headers={"WWW-Authenticate": "ApiKey"},
            )
        
        # Validate API key
        if api_key not in VALID_API_KEYS:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=401,
                content={
                    "error": "Invalid API key",
                    "message": "The provided API key is not valid",
                    "code": "INVALID_API_KEY"
                },
                headers={"WWW-Authenticate": "ApiKey"},
            )
        
        key_data = VALID_API_KEYS[api_key]
        
        # Check for expired keys
        if key_data.get("status") == "expired":
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=401,
                content={
                    "error": "API key expired",
                    "message": "The provided API key has expired",
                    "code": "EXPIRED_API_KEY"
                },
                headers={"WWW-Authenticate": "ApiKey"},
            )
        
        # Check rate limits
        if key_data["requests_left"] <= 0:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": "API key has exceeded its rate limit",
                    "code": "RATE_LIMIT_EXCEEDED"
                },
                headers={"Retry-After": "3600"},
            )
        
        # Decrement request count (in real app, this would be in a database)
        if key_data["requests_left"] != float('inf'):
            key_data["requests_left"] -= 1
    
    response = await call_next(request)
    return response

# Mount the MCP app
app.mount("/mcp", mcp.streamable_http_app())

# Health check endpoint (no auth required)
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "auth": "api-key"}

# Auth info endpoint (no auth required)
@app.get("/auth-info")
async def auth_info():
    """Get authentication information for testing."""
    return {
        "auth_type": "api_key",
        "header_name": "X-API-Key",
        "endpoint": "/mcp", 
        "valid_keys": list(VALID_API_KEYS.keys()),
        "example_header": "X-API-Key: sk-test-key-123",
        "test_keys": {
            "sk-test-key-123": "Pro plan user with 1000 requests",
            "sk-demo-key-456": "Demo user with 10 requests", 
            "sk-admin-key-789": "Admin user with unlimited requests",
            "sk-expired-key": "Expired key (will fail)",
            "sk-limited-key": "Limited user with 1 request"
        }
    }

if __name__ == "__main__":
    print("🚀 Starting API Key Authentication MCP Test Server")
    print("🔐 Authentication: X-API-Key Header")
    print("🔗 Endpoint: http://localhost:8002/mcp")
    print("🛠️  Tools available: get_weather, send_notification, list_documents, ai_analysis")
    print("📦 Resources available: api://usage")
    print("-" * 70)
    print("🔑 Valid test API keys:")
    for key, data in VALID_API_KEYS.items():
        status = f" ({data.get('status', 'active')})" if data.get('status') else ""
        print(f"  • {key}: {data['user']} ({data['plan']}){status}")
    print("-" * 70)
    print("🧪 Test commands:")
    print("  # Valid request:")
    print('  curl -H "X-API-Key: sk-test-key-123" http://localhost:8002/mcp')
    print("  # Invalid request (should fail):")
    print('  curl http://localhost:8002/mcp')
    print("  # Auth info:")
    print('  curl http://localhost:8002/auth-info')
    print("-" * 70)
    print("💡 Use Ctrl+C to stop the server")
    
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8002,
        log_level="info"
    )
