# Standard library imports
import logging
import os
import sys
from contextlib import AsyncExitStack, asynccontextmanager
from typing import (
    Any,
    Awaitable,
    Callable,
    cast,
    NoReturn,
    NotRequired,
    TextIO,
    TypeAlias,
    TypedDict,
)
from urllib.parse import urlparse
import time

# Third-party imports
try:
    from anyio.streams.memory import (
        MemoryObjectReceiveStream,
        MemoryObjectSendStream,
    )
    import httpx
    from jsonschema_pydantic import jsonschema_to_pydantic  # type: ignore
    from langchain_core.tools import BaseTool, ToolException
    from mcp import ClientSession
    from mcp.client.sse import sse_client
    from mcp.client.stdio import stdio_client, StdioServerParameters
    from mcp.client.streamable_http import streamablehttp_client
    from mcp.client.websocket import websocket_client
    from mcp.shared._httpx_utils import McpHttpClientFactory
    import mcp.types as mcp_types
    from pydantic import BaseModel
    # from pydantic_core import to_json
except ImportError as e:
    print(f"\nError: Required package not found: {e}")
    print("Please ensure all required packages are installed\n")
    sys.exit(1)


class McpServerCommandBasedConfig(TypedDict):
    """Configuration for an MCP server launched via command line.

    This configuration is used for local MCP servers that are started as child
    processes using the stdio client. It defines the command to run, optional
    arguments, environment variables, working directory, and error logging
    options.

    Attributes:
        command: The executable command to run (e.g., "npx", "uvx", "python").
        args: Optional list of command-line arguments to pass to the command.
        env: Optional dictionary of environment variables to set for the
                process.
        cwd: Optional working directory where the command will be executed.
        errlog: Optional file-like object for redirecting the server's stderr
                output.

    Example:
        {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "."],
            "env": {"NODE_ENV": "production"},
            "cwd": "/path/to/working/directory",
            "errlog": open("server.log", "w")
        }
    """
    command: str
    args: NotRequired[list[str] | None]
    env: NotRequired[dict[str, str] | None]
    cwd: NotRequired[str | None]
    errlog: NotRequired[TextIO | None]


class McpServerUrlBasedConfig(TypedDict):
    """Configuration for a remote MCP server accessed via URL.

    This configuration is used for remote MCP servers that are accessed via
    HTTP/HTTPS (Streamable HTTP, Server-Sent Events) or WebSocket connections.
    It defines the URL to connect to and optional HTTP headers for authentication.

    Note: Per MCP spec, clients should try Streamable HTTP first, then fallback 
    to SSE on 4xx errors for maximum compatibility.

    Attributes:
        url: The URL of the remote MCP server. For HTTP/HTTPS servers,
                use http:// or https:// prefix. For WebSocket servers,
                use ws:// or wss:// prefix.
        transport: Optional transport type. Supported values:
                "streamable_http" (recommended, attempted first), 
                "sse" (legacy, fallback), "websocket"
        headers: Optional dictionary of HTTP headers to include in the request,
                typically used for authentication (e.g., bearer tokens).
        timeout: Optional timeout for HTTP requests (default: 30.0 seconds).
        sse_read_timeout: Optional timeout for SSE connections (SSE only).
        terminate_on_close: Optional flag to terminate on connection close.
        httpx_client_factory: Optional factory for creating HTTP clients.
        auth: Optional httpx authentication for requests.

    Example for auto-detection (recommended):
        {
            "url": "https://api.example.com/mcp",
            # Auto-tries Streamable HTTP first, falls back to SSE on 4xx
            "headers": {"Authorization": "Bearer token123"},
            "timeout": 60.0
        }

    Example for explicit Streamable HTTP:
        {
            "url": "https://api.example.com/mcp",
            "transport": "streamable_http",
            "headers": {"Authorization": "Bearer token123"},
            "timeout": 60.0
        }

    Example for explicit SSE (legacy):
        {
            "url": "https://example.com/mcp/sse",
            "transport": "sse",
            "headers": {"Authorization": "Bearer token123"}
        }

    Example for WebSocket:
        {
            "url": "wss://example.com/mcp/ws",
            "transport": "websocket"
        }
    """
    url: str
    transport: NotRequired[str]
    headers: NotRequired[dict[str, str] | None]
    timeout: NotRequired[float]
    sse_read_timeout: NotRequired[float]
    terminate_on_close: NotRequired[bool]
    httpx_client_factory: NotRequired[McpHttpClientFactory]
    auth: NotRequired[httpx.Auth]

# Type for a single MCP server configuration, which can be either
# command-based or URL-based.
SingleMcpServerConfig = McpServerCommandBasedConfig | McpServerUrlBasedConfig
"""Configuration for a single MCP server, either command-based or URL-based.

This type represents the configuration for a single MCP server, which can
be either:
1. A local server launched via command line (McpServerCommandBasedConfig)
2. A remote server accessed via URL (McpServerUrlBasedConfig)

The type is determined by the presence of either the "command" key
(for command-based) or the "url" key (for URL-based).
"""

# Configuration dictionary for multiple MCP servers
McpServersConfig = dict[str, SingleMcpServerConfig]
"""Configuration dictionary for multiple MCP servers.

A dictionary mapping server names (as strings) to their respective
configurations. Each server name acts as a logical identifier used for logging
and debugging. The configuration for each server can be either command-based
or URL-based.

Example:
    {
        "filesystem": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "."]
        },
        "fetch": {
            "command": "uvx",
            "args": ["mcp-server-fetch"]
        },
        "auto-detection-server": {
            "url": "https://api.example.com/mcp",
            # Will try Streamable HTTP first, fallback to SSE on 4xx
            "headers": {"Authorization": "Bearer token123"},
            "timeout": 60.0
        },
        "explicit-sse-server": {
            "url": "https://legacy.example.com/mcp/sse",
            "transport": "sse",
            "headers": {"Authorization": "Bearer token123"}
        }
    }
"""


def fix_schema(schema: dict) -> dict:
    """Converts JSON Schema "type": ["string", "null"] to "anyOf" format.

    Args:
        schema: A JSON schema dictionary

    Returns:
        Modified schema with converted type formats
    """
    if isinstance(schema, dict):
        if "type" in schema and isinstance(schema["type"], list):
            schema["anyOf"] = [{"type": t} for t in schema["type"]]
            del schema["type"]  # Remove "type" and standardize to "anyOf"
        for key, value in schema.items():
            schema[key] = fix_schema(value)  # Apply recursively
    return schema


# Type alias for the bidirectional communication channels with the MCP server
# FIXME: not defined in mcp.types, really?
Transport: TypeAlias = tuple[
    MemoryObjectReceiveStream[mcp_types.JSONRPCMessage | Exception],
    MemoryObjectSendStream[mcp_types.JSONRPCMessage]
]


def is_4xx_error(error: Exception) -> bool:
    """Enhanced 4xx error detection matching TypeScript implementation.
    
    Used to decide whether to fall back from Streamable HTTP to SSE transport
    per MCP specification. Handles various error types and patterns that indicate
    4xx-like conditions.
    
    Args:
        error: The error to check
        
    Returns:
        True if the error represents a 4xx HTTP status or equivalent
    """
    if not error:
        return False
    
    # Handle ExceptionGroup (Python 3.11+) by checking sub-exceptions
    if hasattr(error, 'exceptions'):
        return any(is_4xx_error(sub_error) for sub_error in error.exceptions)
    
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


async def test_streamable_http_support(
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
        async with httpx.AsyncClient() as client:
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
        if is_4xx_error(e):
            logger.debug(f"4xx-like error detected: {e}")
            return False
        raise


def validate_mcp_server_config(
    server_name: str,
    server_config: SingleMcpServerConfig,
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
        ValueError: If configuration is invalid
    """
    has_url = "url" in server_config and server_config["url"] is not None
    has_command = "command" in server_config and server_config["command"] is not None
    
    # Get transport type (prefer 'transport' over 'type' for compatibility)
    transport_type = server_config.get("transport") or server_config.get("type")
    
    # Conflict check: Both url and command specified
    if has_url and has_command:
        raise ValueError(
            f'MCP server "{server_name}": Cannot specify both "url" ({server_config["url"]}) '
            f'and "command" ({server_config["command"]}). Use "url" for remote servers '
            f'or "command" for local servers.'
        )
    
    # Must have either URL or command
    if not has_url and not has_command:
        raise ValueError(
            f'MCP server "{server_name}": Either "url" or "command" must be specified'
        )
    
    if has_url:
        url_str = str(server_config["url"])
        try:
            parsed_url = urlparse(url_str)
            url_scheme = parsed_url.scheme.lower()
        except Exception:
            raise ValueError(
                f'MCP server "{server_name}": Invalid URL format: {url_str}'
            )
        
        if transport_type:
            transport_lower = transport_type.lower()
            
            # Check transport/URL protocol compatibility
            if transport_lower in ["http", "streamable_http"] and url_scheme not in ["http", "https"]:
                raise ValueError(
                    f'MCP server "{server_name}": Transport "{transport_type}" requires '
                    f'http:// or https:// URL, but got: {url_scheme}://'
                )
            elif transport_lower == "sse" and url_scheme not in ["http", "https"]:
                raise ValueError(
                    f'MCP server "{server_name}": Transport "sse" requires '
                    f'http:// or https:// URL, but got: {url_scheme}://'
                )
            elif transport_lower in ["ws", "websocket"] and url_scheme not in ["ws", "wss"]:
                raise ValueError(
                    f'MCP server "{server_name}": Transport "{transport_type}" requires '
                    f'ws:// or wss:// URL, but got: {url_scheme}://'
                )
            elif transport_lower == "stdio":
                raise ValueError(
                    f'MCP server "{server_name}": Transport "stdio" requires "command", '
                    f'but "url" was provided'
                )
        
        # Validate URL scheme is supported
        if url_scheme not in ["http", "https", "ws", "wss"]:
            raise ValueError(
                f'MCP server "{server_name}": Unsupported URL scheme "{url_scheme}". '
                f'Supported schemes: http, https, ws, wss'
            )
    
    elif has_command:
        if transport_type:
            transport_lower = transport_type.lower()
            
            # Check transport requires command
            if transport_lower == "stdio":
                pass  # Valid
            elif transport_lower in ["http", "streamable_http", "sse", "ws", "websocket"]:
                raise ValueError(
                    f'MCP server "{server_name}": Transport "{transport_type}" requires "url", '
                    f'but "command" was provided'
                )
            else:
                logger.warning(
                    f'MCP server "{server_name}": Unknown transport type "{transport_type}", '
                    f'treating as stdio'
                )


async def connect_to_mcp_server(
    server_name: str,
    server_config: SingleMcpServerConfig,
    exit_stack: AsyncExitStack,
    logger: logging.Logger = logging.getLogger(__name__)
) -> Transport:
    """Establishes a connection to an MCP server

    Implements consistent transport selection logic matching TypeScript version:
    
    Transport Selection Priority:
    1. Explicit transport/type field (must match URL protocol if URL provided)
    2. URL protocol auto-detection (http/https → StreamableHTTP, ws/wss → WebSocket)
    3. Command presence → Stdio transport
    4. Error if none of the above match
    
    For HTTP URLs without explicit transport, follows MCP specification backwards
    compatibility: try Streamable HTTP first, fallback to SSE on 4xx errors.

    Supports multiple transport types:
    - stdio: For local command-based servers
    - streamable_http, http: For Streamable HTTP servers
    - sse: For Server-Sent Events HTTP servers (legacy)
    - websocket, ws: For WebSocket servers

    Args:
        server_name: Server instance name to use for better logging
        server_config: Configuration dictionary for server setup
        exit_stack: Context manager for cleanup handling
        logger: Logger instance for debugging and monitoring

    Returns:
        A tuple of receive and send streams for server communication

    Raises:
        ValueError: If configuration is invalid
        Exception: If server initialization fails
    """
    try:
        logger.info(f'MCP server "{server_name}": '
                    f"initializing with: {server_config}")

        # Validate configuration first
        validate_mcp_server_config(server_name, server_config, logger)
        
        # Determine if URL-based or command-based
        has_url = "url" in server_config and server_config["url"] is not None
        has_command = "command" in server_config and server_config["command"] is not None
        
        # Get transport type (prefer 'transport' over 'type')
        transport_type = server_config.get("transport") or server_config.get("type")
        
        if has_url:
            # URL-based configuration
            url_config = cast(McpServerUrlBasedConfig, server_config)
            url_str = str(url_config["url"])
            parsed_url = urlparse(url_str)
            url_scheme = parsed_url.scheme.lower()
            
            # Extract common parameters
            headers = url_config.get("headers", None)
            timeout = url_config.get("timeout", None)
            auth = url_config.get("auth", None)
            
            if url_scheme in ["http", "https"]:
                # HTTP/HTTPS: Handle explicit transport or auto-detection
                
                if transport_type and transport_type.lower() in ["streamable_http", "http"]:
                    # Explicit Streamable HTTP (no fallback)
                    logger.info(f'MCP server "{server_name}": '
                               f"connecting via Streamable HTTP (explicit) to {url_str}")
                    
                    kwargs = {}
                    if headers is not None:
                        kwargs["headers"] = headers
                    if timeout is not None:
                        kwargs["timeout"] = timeout
                    if auth is not None:
                        kwargs["auth"] = auth
                    
                    transport = await exit_stack.enter_async_context(
                        streamablehttp_client(url_str, **kwargs)
                    )
                    
                elif transport_type and transport_type.lower() == "sse":
                    # Explicit SSE (no fallback)
                    logger.info(f'MCP server "{server_name}": '
                               f"connecting via SSE (explicit) to {url_str}")
                    logger.warning(f'MCP server "{server_name}": '
                                  f"SSE transport is deprecated, consider migrating to streamable_http")
                    
                    transport = await exit_stack.enter_async_context(
                        sse_client(url_str, headers=headers)
                    )
                    
                else:
                    # Auto-detection: URL protocol suggests HTTP transport, try Streamable HTTP first
                    logger.debug(f'MCP server "{server_name}": '
                                f"auto-detecting HTTP transport using MCP specification method")
                    
                    try:
                        logger.info(f'MCP server "{server_name}": '
                                   f"testing Streamable HTTP support for {url_str}")
                        
                        supports_streamable = await test_streamable_http_support(
                            url_str, 
                            headers=headers,
                            timeout=timeout,
                            auth=auth,
                            logger=logger
                        )
                        
                        if supports_streamable:
                            logger.info(f'MCP server "{server_name}": '
                                       f"detected Streamable HTTP transport support")
                            
                            kwargs = {}
                            if headers is not None:
                                kwargs["headers"] = headers
                            if timeout is not None:
                                kwargs["timeout"] = timeout
                            if auth is not None:
                                kwargs["auth"] = auth
                            
                            transport = await exit_stack.enter_async_context(
                                streamablehttp_client(url_str, **kwargs)
                            )
                        else:
                            logger.info(f'MCP server "{server_name}": '
                                       f"received 4xx error, falling back to SSE transport")
                            logger.warning(f'MCP server "{server_name}": '
                                          f"Using SSE transport (deprecated), server should support Streamable HTTP")
                            
                            transport = await exit_stack.enter_async_context(
                                sse_client(url_str, headers=headers)
                            )
                            
                    except Exception as error:
                        logger.error(f'MCP server "{server_name}": '
                                    f"transport detection failed: {error}")
                        raise
                        
            elif url_scheme in ["ws", "wss"]:
                # WebSocket transport
                if transport_type and transport_type.lower() not in ["websocket", "ws"]:
                    logger.warning(f'MCP server "{server_name}": '
                                  f'URL scheme "{url_scheme}" suggests WebSocket, '
                                  f'but transport "{transport_type}" specified')
                
                logger.info(f'MCP server "{server_name}": '
                           f"connecting via WebSocket to {url_str}")
                
                transport = await exit_stack.enter_async_context(
                    websocket_client(url_str)
                )
                
            else:
                # This should be caught by validation, but include for safety
                raise ValueError(
                    f'MCP server "{server_name}": Unsupported URL scheme "{url_scheme}". '
                    f'Supported schemes: http/https (for streamable_http/sse), ws/wss (for websocket)'
                )
                
        elif has_command:
            # Command-based configuration (stdio transport)
            if transport_type and transport_type.lower() not in ["stdio", ""]:
                logger.warning(f'MCP server "{server_name}": '
                              f'Command provided suggests stdio transport, '
                              f'but transport "{transport_type}" specified')
            
            logger.info(f'MCP server "{server_name}": '
                        f"spawning local process via stdio")
            
            # NOTE: `uv` and `npx` seem to require PATH to be set.
            # To avoid confusion, it was decided to automatically append it
            # to the env if not explicitly set by the config.
            config = cast(McpServerCommandBasedConfig, server_config)
            # env = config.get("env", {}) doesn't work since it can yield None
            env_val = config.get("env")
            env = {} if env_val is None else dict(env_val)
            if "PATH" not in env:
                env["PATH"] = os.environ.get("PATH", "")

            # Use stdio client for commands
            # args = config.get("args", []) doesn't work since it can yield None
            args_val = config.get("args")
            args = [] if args_val is None else list(args_val)
            server_parameters = StdioServerParameters(
                command=config.get("command", ""),
                args=args,
                env=env,
                cwd=config.get("cwd", None)
            )

            # Initialize stdio client and register it with exit stack for cleanup
            errlog_val = config.get("errlog")
            kwargs = {"errlog": errlog_val} if errlog_val is not None else {}
            transport = await exit_stack.enter_async_context(
                stdio_client(server_parameters, **kwargs)
            )
        
        else:
            # This should be caught by validation, but include for safety
            raise ValueError(
                f'MCP server "{server_name}": Invalid configuration - '
                f'either "url" or "command" must be specified'
            )
            
    except Exception as e:
        logger.error(f'MCP server "{server_name}": error during initialization: {str(e)}')
        raise

    return transport


async def get_mcp_server_tools(
    server_name: str,
    transport: Transport,
    exit_stack: AsyncExitStack,
    logger: logging.Logger = logging.getLogger(__name__)
) -> list[BaseTool]:
    """Retrieves and converts MCP server tools to LangChain format.

    Args:
        server_name: Server instance name to use for better logging
        transport: Communication channels tuple
        exit_stack: Context manager for cleanup handling
        logger: Logger instance for debugging and monitoring

    Returns:
        List of LangChain tools converted from MCP tools

    Raises:
        Exception: If tool conversion fails
    """
    try:
        # Handle both 2-tuple (SSE, stdio) and 3-tuple (streamable HTTP) returns
        if len(transport) == 2:
            read, write = transport
        elif len(transport) == 3:
            read, write, _ = transport  # Third element is session info/metadata
        else:
            raise ValueError(f"Unexpected transport tuple length: {len(transport)}")

        # Use an intermediate `asynccontextmanager` to log the cleanup message
        @asynccontextmanager
        async def log_before_aexit(context_manager, message):
            """Helper context manager that logs before cleanup"""
            yield await context_manager.__aenter__()
            try:
                logger.info(message)
            finally:
                await context_manager.__aexit__(None, None, None)

        # Initialize client session with cleanup logging
        session = await exit_stack.enter_async_context(
            log_before_aexit(
                ClientSession(read, write),
                f'MCP server "{server_name}": session closed'
            )
        )

        await session.initialize()
        logger.info(f'MCP server "{server_name}": connected')

        # Get MCP tools
        tools_response = await session.list_tools()

        # Wrap MCP tools into LangChain tools
        langchain_tools: list[BaseTool] = []
        for tool in tools_response.tools:

            # Define adapter class to convert MCP tool to LangChain format
            class McpToLangChainAdapter(BaseTool):
                name: str = tool.name or "NO NAME"
                description: str = tool.description or ""
                # Convert JSON schema to Pydantic model for argument validation
                args_schema: type[BaseModel] = jsonschema_to_pydantic(
                    fix_schema(tool.inputSchema)  # Apply schema conversion
                )
                session: ClientSession | None = None

                def _run(self, **kwargs: Any) -> NoReturn:
                    raise NotImplementedError(
                        "MCP tools only support async operations"
                    )

                async def _arun(self, **kwargs: Any) -> Any:
                    """Asynchronously executes the tool with given arguments.

                    Logs input/output and handles errors.

                    Args:
                        **kwargs: Arguments to be passed to the MCP tool

                    Returns:
                        Formatted response from the MCP tool as a string

                    Raises:
                        ToolException: If the tool execution fails
                    """
                    logger.info(f'MCP tool "{server_name}"/"{tool.name}" '
                                f"received input: {kwargs}")

                    try:
                        result = await session.call_tool(self.name, kwargs)

                        if hasattr(result, "isError") and result.isError:
                            raise ToolException(
                                f"Tool execution failed: {result.content}"
                            )

                        if not hasattr(result, "content"):
                            return str(result)

                        # The return type of `BaseTool`'s `arun` is `str`.
                        try:
                            result_content_text = "\n\n".join(
                                item.text
                                for item in result.content
                                if isinstance(item, mcp_types.TextContent)
                            )
                            # text_items = [
                            #     item
                            #     for item in result.content
                            #     if isinstance(item, mcp_types.TextContent)
                            # ]
                            # result_content_text =to_json(text_items).decode()

                        except KeyError as e:
                            result_content_text = (
                                f"Error in parsing result.content: {str(e)}; "
                                f"contents: {repr(result.content)}"
                            )

                        # Log rough result size for monitoring
                        size = len(result_content_text.encode())
                        logger.info(f'MCP tool "{server_name}"/"{tool.name}" '
                                    f"received result (size: {size})")

                        # If no text content, return a clear message
                        # describing the situation.
                        result_content_text = (
                            result_content_text or
                            "No text content available in response"
                        )

                        return result_content_text

                    except Exception as e:
                        logger.warn(
                            f'MCP tool "{server_name}"/"{tool.name}" '
                            f"caused error:  {str(e)}"
                        )
                        if self.handle_tool_error:
                            return f"Error executing MCP tool: {str(e)}"
                        raise

            langchain_tools.append(McpToLangChainAdapter())

        # Log available tools for debugging
        logger.info(f'MCP server "{server_name}": {len(langchain_tools)} '
                    f"tool(s) available:")
        for tool in langchain_tools:
            logger.info(f"- {tool.name}")
    except Exception as e:
        logger.error(f"Error getting MCP tools: {str(e)}")
        raise

    return langchain_tools


# A very simple pre-configured logger for fallback
def init_logger() -> logging.Logger:
    """Creates a simple pre-configured logger.

    Returns:
        A configured Logger instance
    """
    logging.basicConfig(
        level=logging.INFO,  # More reasonable default level
        format="\x1b[90m[%(levelname)s]\x1b[0m %(message)s"
    )
    # Only set MCP-related loggers to DEBUG for better MCP visibility
    logger = logging.getLogger()
    logging.getLogger("langchain_mcp_tools").setLevel(logging.DEBUG)
    
    # Keep HTTP libraries quieter
    for lib in ["httpx", "urllib3", "requests", "anthropic", "openai"]:
        logging.getLogger(lib).setLevel(logging.WARNING)
    
    return logger


# Type hint for cleanup function
McpServerCleanupFn = Callable[[], Awaitable[None]]
"""Type for the async cleanup function returned by
    convert_mcp_to_langchain_tools.

This represents an asynchronous function that takes no arguments and returns
nothing. It's used to properly shut down all MCP server connections and clean
up resources when the tools are no longer needed.

Example usage:
    tools, cleanup = await convert_mcp_to_langchain_tools(server_configs)
    # Use tools...
    await cleanup()  # Clean up resources when done
"""


async def convert_mcp_to_langchain_tools(
    server_configs: McpServersConfig,
    logger: logging.Logger | None = None
) -> tuple[list[BaseTool], McpServerCleanupFn]:
    """Initialize multiple MCP servers and convert their tools to
    LangChain format.

    This async function manages parallel initialization of multiple MCP
    servers, converts their tools to LangChain format, and provides a cleanup
    mechanism. It orchestrates the full lifecycle of multiple servers.

    Implements MCP specification backwards compatibility: for HTTP URLs,
    automatically tries Streamable HTTP first, then falls back to SSE on 4xx 
    errors for maximum server compatibility.

    Supports multiple transport types:
    - stdio: For local command-based servers
    - streamable_http: For Streamable HTTP servers (tried first for HTTP URLs)
    - sse: For Server-Sent Events HTTP servers (fallback for HTTP URLs)
    - websocket: For WebSocket servers

    Args:
        server_configs: Dictionary mapping server names to their
            configurations, where each configuration contains command, args,
            and env settings for stdio servers, or url, transport, and headers
            for remote servers
        logger: Logger instance to use for logging events and errors.
            If None, uses module logger with fallback to a pre-configured
            logger when no root handlers exist.

    Returns:
        A tuple containing:

        * List of converted LangChain tools from all servers
        * Async cleanup function to properly shutdown all server connections

    Example:

        server_configs = {
            "fetch": {
                "command": "uvx", "args": ["mcp-server-fetch"]
            },
            "weather": {
                "command": "npx", "args": ["-y","@h1deya/mcp-server-weather"]
            },
            "auto-detection-server": {
                "url": "https://api.example.com/mcp",
                # Will auto-try Streamable HTTP, fallback to SSE on 4xx
                "headers": {"Authorization": "Bearer token123"},
                "timeout": 60.0
            },
            "explicit-sse-server": {
                "url": "https://legacy.example.com/mcp/sse",
                "transport": "sse",
                "headers": {"Authorization": "Bearer token123"}
            }
        }

        tools, cleanup = await convert_mcp_to_langchain_tools(server_configs)

        # Use tools...

        await cleanup()
    """

    if logger is None:
        logger = logging.getLogger(__name__)
        # Check if the root logger has handlers configured
        if not logging.root.handlers and not logger.handlers:
            # No logging configured, use a simple pre-configured logger
            logger = init_logger()

    # Initialize AsyncExitStack for managing multiple server lifecycles
    transports: list[Transport] = []
    async_exit_stack = AsyncExitStack()

    # Initialize all MCP servers concurrently
    for server_name, server_config in server_configs.items():
        # NOTE for stdio MCP servers:
        # the following `await` only blocks until the server subprocess
        # is spawned, i.e. after returning from the `await`, the spawned
        # subprocess starts its initialization independently of (so in
        # parallel with) the Python execution of the following lines.
        transport = await connect_to_mcp_server(
            server_name,
            server_config,
            async_exit_stack,
            logger
        )
        transports.append(transport)

    # Convert tools from each server to LangChain format
    langchain_tools: list[BaseTool] = []
    for (server_name, server_config), transport in zip(
        server_configs.items(),
        transports,
        strict=True
    ):
        tools = await get_mcp_server_tools(
            server_name,
            transport,
            async_exit_stack,
            logger
        )
        langchain_tools.extend(tools)

    # Define a cleanup function to properly shut down all servers
    async def mcp_cleanup() -> None:
        """Closes all server connections and cleans up resources."""
        await async_exit_stack.aclose()

    # Log summary of initialized tools
    logger.info(f"MCP servers initialized: {len(langchain_tools)} tool(s) "
                f"available in total")
    for tool in langchain_tools:
        logger.debug(f"- {tool.name}")

    return langchain_tools, mcp_cleanup
