#!/usr/bin/env python3
"""
Streamable HTTP Authentication Test Client for MCP

⚠️ TEST IMPLEMENTATION ONLY - NOT OAUTH 2.1 COMPLIANT

This is a simplified test implementation that does NOT comply with OAuth 2.1 requirements.
It's designed solely for testing MCP authentication integration and transport functionality.

For production use, you MUST implement:
- PKCE (Proof Key for Code Exchange) - REQUIRED in OAuth 2.1
- Authorization Code Flow with proper user consent and authorization server
- Authorization Server Metadata discovery (RFC8414)
- Secure token storage, validation, and refresh
- Dynamic Client Registration (RFC7591) - RECOMMENDED

This test implementation uses:
- Hardcoded tokens (❌ Security risk)
- No real authorization flow (❌ Missing OAuth core)
- Mock PKCE values (❌ Not cryptographically secure)
- No token validation (❌ Missing security)

Key Features:
=============

1. **Test OAuth Provider**: Mock OAuth provider for testing
2. **Bearer Token Auth**: Basic token-based authentication
3. **Streamable HTTP**: Tests Streamable HTTP transport with auth
4. **Auto-Detection**: Tests transport auto-detection
5. **Tool Testing**: Tests authenticated MCP tools

Usage:
======

1. Start the auth test server:
   uv run testfiles/streamable-http-auth-test-server.py

2. Run this client:
   uv run testfiles/streamable-http-auth-test-client.py

Expected Flow:
==============

1. Client creates mock OAuth provider with test tokens
2. Client tests explicit Streamable HTTP connection with auth
3. Client tests transport auto-detection with auth
4. Client tests all available authenticated tools
5. Client cleans up connections
"""

import asyncio
import logging
import os
import sys
from typing import Any, Optional, Dict

try:
    import httpx
except ImportError as e:
    print(f"\nError: Required package not found: {e}")
    print("Please install required packages: pip install httpx")
    sys.exit(1)

# Import the langchain-mcp-tools library
from langchain_mcp_tools import (
    convert_mcp_to_langchain_tools,
    McpServersConfig,
)

# Configuration
SERVER_URL = "http://127.0.0.1:3334"
DEBUG = True


class TestStreamableAuthProvider:
    """
    ⚠️ TEST IMPLEMENTATION ONLY - NOT OAUTH 2.1 COMPLIANT
    
    This test provider implements a simplified authentication mechanism that does NOT
    comply with OAuth 2.1 requirements. It's designed solely for testing MCP 
    authentication integration with Streamable HTTP transport.
    
    For production use, implement a proper OAuth 2.1 client with:
    - PKCE (Proof Key for Code Exchange) - REQUIRED in OAuth 2.1
    - Authorization Code Flow with proper user consent flow
    - Authorization Server Metadata discovery (RFC8414)
    - Secure token storage, validation, and refresh
    - Dynamic Client Registration (RFC7591) - RECOMMENDED
    """
    
    def __init__(self):
        """Initialize the test auth provider."""
        self._client_info = {"client_id": "test_streamable_client_id"}
        self._tokens = {
            "access_token": "test_token_test_streamable_client_id",
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": "refresh_token_streamable"
        }
        self._code_verifier = "test_code_verifier_streamable"
    
    @property
    def redirect_url(self) -> str:
        """Get redirect URL."""
        return "http://localhost:3000/callback"
    
    @property
    def client_metadata(self) -> Dict[str, Any]:
        """Get client metadata."""
        return {
            "client_name": "Test Streamable HTTP Client",
            "redirect_uris": ["http://localhost:3000/callback"]
        }
    
    async def client_information(self) -> Dict[str, Any]:
        """Get client information."""
        return self._client_info
    
    async def save_client_information(self, info: Dict[str, Any]) -> None:
        """Save client information."""
        self._client_info = info
    
    async def tokens(self) -> Dict[str, Any]:
        """Get current tokens."""
        return self._tokens
    
    async def save_tokens(self, tokens: Dict[str, Any]) -> None:
        """Save tokens."""
        self._tokens = tokens
    
    async def code_verifier(self) -> str:
        """Get code verifier."""
        return self._code_verifier
    
    async def save_code_verifier(self, verifier: str) -> None:
        """Save code verifier."""
        self._code_verifier = verifier
    
    async def redirect_to_authorization(self, url: str) -> None:
        """Handle authorization redirect."""
        raise Exception("Auth required")


# Enhanced logging
class Logger:
    """Enhanced logger with colored output."""
    
    def info(self, *args: Any) -> None:
        print("ℹ️", *args)
    
    def warn(self, *args: Any) -> None:
        print("⚠️", *args)
    
    def error(self, *args: Any) -> None:
        print("❌", *args)
    
    def debug(self, *args: Any) -> None:
        if DEBUG:
            print("🔍", *args)
    
    def success(self, *args: Any) -> None:
        print("✅", *args)


def setup_debug_logging():
    """Set up enhanced debug logging for HTTP requests."""
    # This would normally patch httpx or similar, but for simplicity
    # we'll just enable debug mode
    if DEBUG:
        logging.basicConfig(level=logging.DEBUG)


async def check_server_availability(logger: Logger) -> bool:
    """
    Check if the server is running and available.
    
    Args:
        logger: Logger instance
        
    Returns:
        bool: True if server is available, False otherwise
    """
    try:
        logger.info("Testing server connection...")
        async with httpx.AsyncClient() as client:
            response = await client.get(SERVER_URL, timeout=10.0)
            if response.status_code != 200:
                raise httpx.HTTPStatusError(
                    f"Server error: {response.status_code}",
                    request=response.request,
                    response=response
                )
        logger.success("Server is running")
        return True
    except Exception as error:
        logger.error(f"Server unavailable: {error}")
        logger.info("Make sure to start the server with: uv run testfiles/streamable-http-auth-test-server.py")
        return False


async def test_explicit_streamable_connection(logger: Logger, auth_provider: TestStreamableAuthProvider) -> bool:
    """
    Test explicit Streamable HTTP connection with authentication.
    
    Args:
        logger: Logger instance
        auth_provider: Authentication provider
        
    Returns:
        bool: True if test passed, False otherwise
    """
    logger.info("\n--- Testing Explicit Streamable HTTP Transport ---")
    
    try:
        # Create timeout for connection
        timeout = 60.0
        
        tokens = await auth_provider.tokens()
        token_preview = tokens["access_token"][:20] + "..."
        logger.info(f"Using access token: {token_preview}")
        
        client_info = await auth_provider.client_information()
        logger.debug(f"Auth provider ready with client ID: {client_info['client_id']}")
        
        logger.info(f"Using URL: {SERVER_URL}/mcp")
        logger.info("Using transport: Streamable HTTP")
        logger.info(f"Using access token type: {tokens['token_type']}")
        
        # Configure MCP servers for explicit Streamable HTTP with auth
        mcp_servers: McpServersConfig = {
            "secure_streamable_server": {
                "url": f"{SERVER_URL}/mcp",
                "transport": "streamable_http",  # Explicit
                "headers": {
                    "Authorization": f"{tokens['token_type']} {tokens['access_token']}"
                }
                # In a real implementation, you might pass the auth_provider here
                # "streamable_http_options": {"auth_provider": auth_provider}
            }
        }
        
        # Convert tools with timeout
        result = await asyncio.wait_for(
            convert_mcp_to_langchain_tools(mcp_servers),
            timeout=timeout
        )
        
        tools, cleanup = result
        
        logger.success("Explicit Streamable HTTP connection established!")
        logger.info(f"Available tools: {[tool.name for tool in tools]}")
        
        # Test tools with explicit connection
        if tools:
            echo_tool = next((t for t in tools if t.name == "echo"), None)
            info_tool = next((t for t in tools if t.name == "server-info"), None)
            
            if echo_tool:
                logger.info("Testing echo tool...")
                result = await echo_tool._arun(message="Hello from Streamable HTTP!")
                logger.success(f"Echo tool result: {result}")
            
            if info_tool:
                logger.info("Testing server-info tool...")
                result = await info_tool._arun()
                logger.success(f"Server-info result: {result}")
        
        # Clean up explicit connection
        await cleanup()
        logger.success("Explicit connection cleaned up")
        return True
        
    except asyncio.TimeoutError:
        logger.error("Connection timeout (60s)")
        return False
    except Exception as error:
        logger.error(f"Test failed: {error}")
        return False


async def test_auto_detection_connection(logger: Logger, auth_provider: TestStreamableAuthProvider) -> bool:
    """
    Test auto-detection connection (should use Streamable HTTP).
    
    Args:
        logger: Logger instance
        auth_provider: Authentication provider
        
    Returns:
        bool: True if test passed, False otherwise
    """
    logger.info("\n--- Testing Auto-Detection (should use Streamable HTTP) ---")
    
    try:
        # Create timeout for connection
        timeout = 60.0
        
        tokens = await auth_provider.tokens()
        
        # Configure MCP servers for auto-detection with auth
        mcp_servers: McpServersConfig = {
            "auto_streamable_server": {
                "url": f"{SERVER_URL}/mcp",
                # No transport specified - should auto-detect and use Streamable HTTP
                "headers": {
                    "Authorization": f"{tokens['token_type']} {tokens['access_token']}"
                }
                # In a real implementation, you might pass the auth_provider here
                # "streamable_http_options": {"auth_provider": auth_provider}
            }
        }
        
        # Convert tools with timeout
        result = await asyncio.wait_for(
            convert_mcp_to_langchain_tools(mcp_servers),
            timeout=timeout
        )
        
        tools, cleanup = result
        
        logger.success("Auto-detection connection established!")
        logger.info(f"Available tools: {[tool.name for tool in tools]}")
        
        # Test tools with auto-detection
        if tools:
            echo_tool = next((t for t in tools if t.name == "echo"), None)
            if echo_tool:
                logger.info("Testing echo tool with auto-detection...")
                result = await echo_tool._arun(message="Hello from auto-detected Streamable HTTP!")
                logger.success(f"Auto-detection echo result: {result}")
        
        # Clean up auto-detection connection
        await cleanup()
        logger.success("Auto-detection connection cleaned up")
        return True
        
    except asyncio.TimeoutError:
        logger.error("Connection timeout (60s)")
        return False
    except Exception as error:
        logger.error(f"Test failed: {error}")
        return False


async def main() -> None:
    """Main test function."""
    logger = Logger()
    logger.info("=== MCP STREAMABLE HTTP AUTH TEST ===")
    setup_debug_logging()
    
    # Check server availability
    if not await check_server_availability(logger):
        return
    
    # Create auth provider and prepare for connection
    auth_provider = TestStreamableAuthProvider()
    tokens = await auth_provider.tokens()
    token_preview = tokens["access_token"][:20] + "..."
    logger.info(f"Using access token: {token_preview}")
    
    client_info = await auth_provider.client_information()
    logger.debug(f"Auth provider ready with client ID: {client_info['client_id']}")
    
    # Run tests
    tests_passed = 0
    total_tests = 2
    
    # Test explicit Streamable HTTP connection
    if await test_explicit_streamable_connection(logger, auth_provider):
        tests_passed += 1
    
    # Small delay between tests
    await asyncio.sleep(1)
    
    # Test auto-detection
    if await test_auto_detection_connection(logger, auth_provider):
        tests_passed += 1
    
    # Print results
    if tests_passed == total_tests:
        logger.success("\n🎉 All Streamable HTTP authentication tests completed successfully!")
        
        logger.info("\n📋 Authentication Features Demonstrated:")
        logger.info("  ✅ Bearer token authentication")
        logger.info("  ✅ Explicit Streamable HTTP transport")
        logger.info("  ✅ Transport auto-detection")
        logger.info("  ✅ Authenticated tool execution")
        logger.info("  ✅ Proper connection cleanup")
        
        logger.warn("\n⚠️  Remember: This is a TEST implementation only!")
        logger.warn("   For production, implement proper OAuth 2.1 with PKCE.")
    else:
        logger.error(f"\n❌ {total_tests - tests_passed} out of {total_tests} tests failed")
        
        logger.info("\nTroubleshooting tips:")
        logger.info(f"1. Make sure the Streamable HTTP server is running at: {SERVER_URL}")
        logger.info("2. Start server: uv run testfiles/streamable-http-auth-test-server.py")
        logger.info("3. Verify the token format matches what the server expects")
        logger.info("4. Check network connectivity and firewall settings")
        logger.info("5. Ensure MCP SDK supports Streamable HTTP transport")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as error:
        print(f"\nUnhandled error: {error}")
        sys.exit(1)
