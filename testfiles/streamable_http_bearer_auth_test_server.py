#!/usr/bin/env python3
"""
FastMCP Bearer Token Authentication Test Server with Auto-Cleanup
"""

import atexit
import signal
import sys
import os
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.server.auth import BearerAuthProvider
from fastmcp.server.auth.providers.bearer import RSAKeyPair

# Token file path
TOKEN_FILE = Path(".test_token")

def cleanup_token_file():
    """Remove the token file if it exists."""
    try:
        if TOKEN_FILE.exists():
            TOKEN_FILE.unlink()
            print("🧹 Cleaned up token file")
    except Exception as e:
        print(f"⚠️  Warning: Could not clean up token file: {e}")

def setup_cleanup_handlers():
    """Set up cleanup handlers for various termination scenarios."""
    # Register cleanup for normal exit
    atexit.register(cleanup_token_file)
    
    # Register cleanup for SIGINT (Ctrl+C) and SIGTERM
    def signal_handler(signum, frame):
        print(f"\n🛑 Received signal {signum}, cleaning up...")
        cleanup_token_file()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Termination signal
    
    # On Windows, also handle SIGBREAK (Ctrl+Break)
    if hasattr(signal, 'SIGBREAK'):
        signal.signal(signal.SIGBREAK, signal_handler)

# For testing, generate a key pair
key_pair = RSAKeyPair.generate()

# Create the auth provider
auth = BearerAuthProvider(
    public_key=key_pair.public_key,
    issuer="test-auth-server",
    audience="mcp-test-client"
)

# Create FastMCP server with auth
mcp = FastMCP(
    name="BearerAuthTestServer",
    auth=auth
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
    # Set up cleanup handlers FIRST
    setup_cleanup_handlers()
    
    print("🚀 Starting FastMCP Bearer Token Authentication Test Server")
    print("🔐 Authentication: Built-in BearerAuthProvider")
    print("🔗 Endpoint: http://localhost:8001/mcp")
    print("🛠️  Tools available: authenticated_echo, get_user_info, secure_add")
    print("📦 Resources available: user://profile")
    print("-" * 70)
    
    # Generate and save test token
    test_token = key_pair.create_token(
        issuer="test-auth-server",
        audience="mcp-test-client",
        subject="test-user"
    )
    
    try:
        # Save token to file
        TOKEN_FILE.write_text(test_token)
        print(f"💾 Test token saved to {TOKEN_FILE}")
        
        # Add to .gitignore if it exists, or create it
        gitignore_path = Path(".gitignore")
        gitignore_content = ""
        if gitignore_path.exists():
            gitignore_content = gitignore_path.read_text()
        
        if ".test_token" not in gitignore_content:
            with gitignore_path.open("a") as f:
                f.write("\n# Test token file\n.test_token\n")
            print("📝 Added .test_token to .gitignore")
        
    except Exception as e:
        print(f"❌ Failed to save token: {e}")
        cleanup_token_file()
        sys.exit(1)
    
    print(f"🔑 Test token: {test_token}")
    print("-" * 70)
    print("🧪 Test command:")
    print(f'  curl -H "Authorization: Bearer {test_token}" http://localhost:8001/mcp')
    print("-" * 70)
    print("💡 Use Ctrl+C to stop the server (token will be auto-cleaned)")
    
    try:
        # Run with Streamable HTTP and authentication
        mcp.run(
            transport="http",
            host="127.0.0.1",
            port=8001,
            path="/mcp"
        )
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Server error: {e}")
    finally:
        # Extra cleanup just in case
        cleanup_token_file()
