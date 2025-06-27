#!/usr/bin/env python3
"""
FastMCP Bearer Token Authentication Test Server
Using FastMCP 2.0's built-in BearerAuthProvider - this is the best practice!
"""

from fastmcp import FastMCP
from fastmcp.server.auth import BearerAuthProvider
from fastmcp.server.auth.providers.bearer import RSAKeyPair  # 👈 Correct import path!

# For testing, generate a key pair (use external OAuth in production)
key_pair = RSAKeyPair.generate()

# Create the auth provider
auth = BearerAuthProvider(
    public_key=key_pair.public_key,  # Note: use .public_key, not .public_key_pem
    # Optional: additional validation
    issuer="test-auth-server",
    audience="mcp-test-client"
)

# Create FastMCP server with auth
mcp = FastMCP(
    name="BearerAuthTestServer",
    auth=auth  # 👈 Built-in auth support!
)

@mcp.tool(description="Echo back text with user information")
def authenticated_echo(message: str) -> str:
    """Echo back a message with authentication context."""
    return f"Authenticated echo: {message}"

@mcp.tool(description="Get current user information")  
def get_user_info() -> str:
    """Get information about the authenticated user."""
    return "User info: authenticated user (token validation successful)"

@mcp.tool(description="Add two numbers (requires authentication)")
def secure_add(a: float, b: float) -> float:
    """Add two numbers securely."""
    return a + b

@mcp.resource("user://profile")
def get_user_profile() -> str:
    """Get user profile information."""
    return "User profile: authenticated user profile data"

if __name__ == "__main__":
    print("🚀 Starting FastMCP Bearer Token Authentication Test Server")
    print("🔐 Authentication: Built-in BearerAuthProvider")
    print("🔗 Endpoint: http://localhost:8001/mcp")
    print("🛠️  Tools available: authenticated_echo, get_user_info, secure_add")
    print("📦 Resources available: user://profile")
    print("-" * 70)
    
    # Generate test token for testing
    test_token = key_pair.create_token(
        issuer="test-auth-server",
        audience="mcp-test-client",
        subject="test-user",
        # Note: scopes parameter might be different, let's try without extra_claims first
    )
    print(f"🔑 Test token: {test_token}")
    print("-" * 70)
    print("🧪 Test command:")
    print(f'  curl -H "Authorization: Bearer {test_token}" http://localhost:8001/mcp')
    print("-" * 70)
    print("💡 Use Ctrl+C to stop the server")
    
    # Run with Streamable HTTP and authentication
    mcp.run(
        transport="http",  # Streamable HTTP
        host="127.0.0.1",
        port=8001,
        path="/mcp"
    )
