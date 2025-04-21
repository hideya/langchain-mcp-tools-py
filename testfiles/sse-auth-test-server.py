#!/usr/bin/env python3
"""
SSE Authentication Test Server for MCP

This server implements a FastAPI application with MCP tools over SSE,
protected by JWT authentication.
"""

import os
from datetime import datetime, timedelta

import jwt
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from mcp.server import FastMCP
from starlette.status import HTTP_401_UNAUTHORIZED

# JWT Configuration - for testing only, don't use this in production!
JWT_SECRET = "MCP_TEST_SECRET"
JWT_ALGORITHM = "HS512"
JWT_TOKEN_EXPIRY = 60  # in minutes

# Create MCP and FastAPI application
mcp = FastMCP("auth-test-mcp",
              port=9000,
              description="MCP Authentication Test Server")
app = FastAPI(title="MCP Auth Test Server")


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


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """
    Authentication middleware to verify JWT tokens.

    Args:
        request: FastAPI request object
        call_next: Next middleware or endpoint function

    Returns:
        Response from the next middleware or endpoint

    Raises:
        HTTPException: If authentication fails
    """
    # Check for Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )

    # Extract and verify token
    token = auth_header.split(" ")[1]
    if verify_jwt(token):
        print("[SERVER] Authentication successful")
        response = await call_next(request)
    else:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    return response


# Define MCP tools
@mcp.tool()
async def hello(name: str) -> str:
    """
    Simple hello world tool that requires authentication.

    Args:
        name: Name to greet

    Returns:
        str: Greeting message
    """
    print(f"[SERVER] Got hello request from {name}")
    return f"Hello, {name}! Authentication successful."


@mcp.tool()
async def echo(message: str) -> str:
    """
    Echo tool that requires authentication.

    Args:
        message: Message to echo

    Returns:
        str: Same message
    """
    print(f"[SERVER] Got echo request: {message}")
    return f"ECHO: {message}"


# Mount the MCP SSE app to the root
app.mount("/", mcp.sse_app())


def print_token_info():
    """Print token information to help with testing"""
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
    port = int(os.environ.get("PORT", 9000))
    print_token_info()
    uvicorn.run(app, host="0.0.0.0", port=port)
