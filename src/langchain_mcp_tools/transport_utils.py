"""Utility functions for MCP server management and validation.

This module contains helper functions used internally by the langchain_mcp_tools
library for schema processing, error handling, authentication validation,
transport testing, configuration validation, transport creation, and logging setup.
"""

import logging
import os
import time
from contextlib import AsyncExitStack
from typing import Any, TypeAlias, cast
from urllib.parse import urlparse

try:
    import httpx
    from anyio.streams.memory import (
        MemoryObjectReceiveStream,
        MemoryObjectSendStream,
    )
    from mcp.client.sse import sse_client
    from mcp.client.stdio import stdio_client, StdioServerParameters
    from mcp.client.streamable_http import streamablehttp_client
    from mcp.client.websocket import websocket_client
    import mcp.types as mcp_types
except ImportError as e:
    print(f"\nError: Required package not found: {e}")
    print("Please ensure all required packages are installed\n")
    import sys
    sys.exit(1)


class McpInitializationError(Exception):
    """Raised when MCP server initialization fails."""
    
    def __init__(self, message: str, server_name: str | None = None):
        self.server_name = server_name
        super().__init__(message)
    
    def __str__(self) -> str:
        if self.server_name:
            return f'MCP server "{self.server_name}": {super().__str__()}'
        return super().__str__()


# Type alias for bidirectional communication channels with MCP servers
# Note: This type is not officially exported by mcp.types but represents
# the standard transport interface used by all MCP client implementations
Transport: TypeAlias = tuple[
    MemoryObjectReceiveStream[mcp_types.JSONRPCMessage | Exception],
    MemoryObjectSendStream[mcp_types.JSONRPCMessage]
]


def _is_4xx_error(error: Exception) -> bool:
    """Enhanced 4xx error detection for transport fallback decisions.
    
    Used to decide whether to fall back from Streamable HTTP to SSE transport
    per MCP specification. Handles various error types and patterns that
    indicate 4xx-like conditions.
    
    Args:
        error: The error to check
        
    Returns:
        True if the error represents a 4xx HTTP status or equivalent
    """
    if not error:
        return False
    
    # Handle ExceptionGroup (Python 3.11+) by checking sub-exceptions
    if hasattr(error, 'exceptions'):
        return any(_is_4xx_error(sub_error) for sub_error in error.exceptions)
    
    # Check for explicit HTTP status codes
    if hasattr(error, 'status') and isinstance(error.status, int):
        return 400 <= error.status < 500
    
    # Check for httpx response errors
    if hasattr(error, 'response') and hasattr(error.response, 'status_code'):
        return 400 <= error.response.status_code < 500
    
    # Check error message for 4xx patterns
    error_str = str(error).lower()
    
    # Look for specific 4xx status codes (enhanced pattern matching)
    if any(code in error_str for code in ['400', '401', '402', '403', '404', '405', '406', '407', '408', '409']):
        return True
    
    # Look for 4xx error names (expanded list matching TypeScript version)
    return any(pattern in error_str for pattern in [
        'bad request',
        'unauthorized',
        'forbidden', 
        'not found',
        'method not allowed',
        'not acceptable',
        'request timeout',
        'conflict'
    ])


async def _validate_auth_before_connection(
    url_str: str, 
    headers: dict[str, str] | None = None, 
    timeout: float = 30.0,
    auth: httpx.Auth | None = None,
    logger: logging.Logger = logging.getLogger(__name__),
    server_name: str = "Unknown"
) -> tuple[bool, str]:
    """Pre-validate authentication with a simple HTTP request before creating MCP connection.
    
    This function helps avoid async generator cleanup bugs in the MCP client library
    by detecting authentication failures early, before the problematic MCP transport
    creation process begins.
    
    For OAuth authentication, this function skips validation since OAuth requires
    a complex flow that cannot be pre-validated with a simple HTTP request.
    Use __pre_validate_authentication=False to skip this validation.
    
    Args:
        url_str: The MCP server URL to test
        headers: Optional HTTP headers (typically containing Authorization)
        timeout: Request timeout in seconds
        auth: Optional httpx authentication object (OAuth providers are skipped)
        logger: Logger for debugging
        server_name: MCP server name to be validated
        
    Returns:
        Tuple of (success: bool, message: str) where:
        - success=True means authentication is valid or OAuth (skipped)
        - success=False means authentication failed with descriptive message
        
    Note:
        This function only validates simple authentication (401, 402, 403 errors).
        OAuth authentication is skipped since it requires complex flows.
    """
    
    # Skip auth validation for httpx.Auth providers (OAuth, etc.)
    # These require complex authentication flows that cannot be pre-validated
    # with a simple HTTP request
    if auth is not None:
        auth_class_name = auth.__class__.__name__
        logger.info(f'MCP server "{server_name}": Skipping auth validation for httpx.Auth provider: {auth_class_name}')
        return True, "httpx.Auth authentication skipped (requires full flow)"
    
    # Create InitializeRequest as per MCP specification (similar to test_streamable_http_support)
    init_request = {
        "jsonrpc": "2.0",
        "id": f"auth-test-{int(time.time() * 1000)}",
        "method": "initialize", 
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "mcp-auth-test",
                "version": "1.0.0"
            }
        }
    }
    
    # Required headers per MCP specification
    request_headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/event-stream'
    }
    if headers:
        request_headers.update(headers)
    
    try:
        async with httpx.AsyncClient() as client:
            logger.debug(f"Pre-validating authentication for: {url_str}")
            response = await client.post(
                url_str,
                json=init_request,
                headers=request_headers,
                timeout=timeout,
                auth=auth
            )
            
            if response.status_code == 401:
                return False, f"Authentication failed (401 Unauthorized): {response.text if hasattr(response, 'text') else 'Unknown error'}"
            elif response.status_code == 402:
                return False, f"Authentication failed (402 Payment Required): {response.text if hasattr(response, 'text') else 'Unknown error'}"
            elif response.status_code == 403:
                return False, f"Authentication failed (403 Forbidden): {response.text if hasattr(response, 'text') else 'Unknown error'}"

            logger.info(f'MCP server "{server_name}": Authentication validation passed: {response.status_code}')
            return True, "Authentication validation passed"
            
    except httpx.HTTPStatusError as e:
        return False, f"HTTP Error ({e.response.status_code}): {e}"
    except (httpx.ConnectError, httpx.TimeoutException) as e:
        return False, f"Connection failed: {e}"
    except Exception as e:
        return False, f"Unexpected error during auth validation: {e}"


async def _test_streamable_http_support(
    url: str, 
    headers: dict[str, str] | None = None,
    timeout: float = 30.0,
    auth: httpx.Auth | None = None,
    logger: logging.Logger = logging.getLogger(__name__)
) -> bool:
    """Test if URL supports Streamable HTTP per official MCP specification.
    
    Follows the MCP specification's recommended approach for backwards compatibility.
    Uses proper InitializeRequest with official protocol version and required headers.
    
    See: https://modelcontextprotocol.io/specification/2025-03-26/basic/transports#backwards-compatibility
    
    Args:
        url: The MCP server URL to test
        headers: Optional HTTP headers
        timeout: Request timeout
        auth: Optional httpx authentication
        logger: Logger for debugging
        
    Returns:
        True if Streamable HTTP is supported, False if should fallback to SSE
        
    Raises:
        Exception: For non-4xx errors that should be re-raised
    """
    # Create InitializeRequest as per MCP specification
    init_request = {
        "jsonrpc": "2.0",
        "id": f"transport-test-{int(time.time() * 1000)}",  # Use milliseconds like TS version
        "method": "initialize", 
        "params": {
            "protocolVersion": "2024-11-05",  # Official MCP Protocol version
            "capabilities": {},
            "clientInfo": {
                "name": "mcp-transport-test",
                "version": "1.0.0"
            }
        }
    }
    
    # Required headers per MCP specification
    request_headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/event-stream'  # Required by spec
    }
    if headers:
        request_headers.update(headers)
    
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            logger.debug(f"Testing Streamable HTTP: POST InitializeRequest to {url}")
            response = await client.post(
                url,
                json=init_request,
                headers=request_headers,
                timeout=timeout,
                auth=auth
            )
            
            logger.debug(f"Transport test response: {response.status_code} {response.headers.get('content-type', 'N/A')}")
            
            if response.status_code == 200:
                # Success indicates Streamable HTTP support
                logger.debug("Streamable HTTP test successful")
                return True
            elif 400 <= response.status_code < 500:
                # 4xx error indicates fallback to SSE per MCP spec
                logger.debug(f"Received {response.status_code}, should fallback to SSE")
                return False
            else:
                # Other errors should be re-raised
                response.raise_for_status()
                return True  # If we get here, it succeeded
                
    except httpx.TimeoutException:
        logger.debug("Request timeout - treating as connection error")
        raise
    except httpx.ConnectError:
        logger.debug("Connection error")
        raise
    except Exception as e:
        # Check if it's a 4xx-like error using improved detection
        if _is_4xx_error(e):
            logger.debug(f"4xx-like error detected: {e}")
            return False
        raise


def _validate_mcp_server_config(
    server_name: str,
    server_config: Any,  # Use Any to avoid circular import, will be properly typed in main file
    logger: logging.Logger
) -> None:
    """Validates MCP server configuration following TypeScript transport selection logic.
    
    Transport Selection Priority:
    1. Explicit transport/type field (must match URL protocol if URL provided)
    2. URL protocol auto-detection (http/https → StreamableHTTP, ws/wss → WebSocket)
    3. Command presence → Stdio transport
    4. Error if none of the above match
    
    Conflicts that cause errors:
    - Both url and command specified
    - transport/type doesn't match URL protocol
    - transport requires URL but no URL provided
    - transport requires command but no command provided
    
    Args:
        server_name: Server instance name for error messages
        server_config: Configuration to validate
        logger: Logger for warnings
        
    Raises:
        McpInitializationError: If configuration is invalid
    """
    has_url = "url" in server_config and server_config["url"] is not None
    has_command = "command" in server_config and server_config["command"] is not None
    
    # Get transport type (prefer 'transport' over 'type' for compatibility)
    transport_type = server_config.get("transport") or server_config.get("type")
    
    # Conflict check: Both url and command specified
    if has_url and has_command:
        raise McpInitializationError(
            f'Cannot specify both "url" ({server_config["url"]}) '
            f'and "command" ({server_config["command"]}). Use "url" for remote servers '
            f'or "command" for local servers.',
            server_name=server_name
        )
    
    # Must have either URL or command
    if not has_url and not has_command:
        raise McpInitializationError(
            'Either "url" or "command" must be specified',
            server_name=server_name
        )
    
    if has_url:
        url_str = str(server_config["url"])
        try:
            parsed_url = urlparse(url_str)
            url_scheme = parsed_url.scheme.lower()
        except Exception:
            raise McpInitializationError(
                f'Invalid URL format: {url_str}',
                server_name=server_name
            )
        
        if transport_type:
            transport_lower = transport_type.lower()
            
            # Check transport/URL protocol compatibility
            if transport_lower in ["http", "streamable_http"] and url_scheme not in ["http", "https"]:
                raise McpInitializationError(
                    f'Transport "{transport_type}" requires '
                    f'http:// or https:// URL, but got: {url_scheme}://',
                    server_name=server_name
                )
            elif transport_lower == "sse" and url_scheme not in ["http", "https"]:
                raise McpInitializationError(
                    f'Transport "sse" requires '
                    f'http:// or https:// URL, but got: {url_scheme}://',
                    server_name=server_name
                )
            elif transport_lower in ["ws", "websocket"] and url_scheme not in ["ws", "wss"]:
                raise McpInitializationError(
                    f'Transport "{transport_type}" requires '
                    f'ws:// or wss:// URL, but got: {url_scheme}://',
                    server_name=server_name
                )
            elif transport_lower == "stdio":
                raise McpInitializationError(
                    f'Transport "stdio" requires "command", '
                    f'but "url" was provided',
                    server_name=server_name
                )
        
        # Validate URL scheme is supported
        if url_scheme not in ["http", "https", "ws", "wss"]:
            raise McpInitializationError(
                f'Unsupported URL scheme "{url_scheme}". '
                f'Supported schemes: http, https, ws, wss',
                server_name=server_name
            )
    
    elif has_command:
        if transport_type:
            transport_lower = transport_type.lower()
            
            # Check transport requires command
            if transport_lower == "stdio":
                pass  # Valid
            elif transport_lower in ["http", "streamable_http", "sse", "ws", "websocket"]:
                raise McpInitializationError(
                    f'Transport "{transport_type}" requires "url", '
                    f'but "command" was provided',
                    server_name=server_name
                )
            else:
                logger.warning(
                    f'MCP server "{server_name}": Unknown transport type "{transport_type}", '
                    f'treating as stdio'
                )
