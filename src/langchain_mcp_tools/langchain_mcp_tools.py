# Public API
__all__ = [
    'convert_mcp_to_langchain_tools',
    'McpServersConfig',
    'SingleMcpServerConfig',
    'McpServerCommandBasedConfig',
    'McpServerUrlBasedConfig',
    'McpInitializationError'
]

# Standard library imports
import logging
import os
import sys
from contextlib import AsyncExitStack, asynccontextmanager
from typing import (
    Awaitable,
    Callable,
    cast,
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
    from langchain_core.tools import BaseTool
    from mcp import ClientSession
    from mcp.client.sse import sse_client
    from mcp.client.stdio import stdio_client, StdioServerParameters
    from mcp.client.streamable_http import streamablehttp_client
    from mcp.client.websocket import websocket_client
    from mcp.shared._httpx_utils import McpHttpClientFactory
    import mcp.types as mcp_types
    # from pydantic_core import to_json
except ImportError as e:
    print(f"\nError: Required package not found: {e}")
    print("Please ensure all required packages are installed\n")
    sys.exit(1)

# Local imports
from .tool_adapter import create_mcp_langchain_adapter
from .transport_utils import (
    Transport,
    McpInitializationError,
    _validate_auth_before_connection,
    _test_streamable_http_support,
    _validate_mcp_server_config,
)


class McpInitializationError(Exception):
    """Raised when MCP server initialization fails."""
    
    def __init__(self, message: str, server_name: str | None = None):
        self.server_name = server_name
        super().__init__(message)
    
    def __str__(self) -> str:
        if self.server_name:
            return f'MCP server "{self.server_name}": {super().__str__()}'
        return super().__str__()


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
                "streamable_http" or "http" (recommended, attempted first), 
                "sse" (deprecated, fallback), "websocket"
        type: Optional alternative field name for transport (for compatibility)
        headers: Optional dictionary of HTTP headers to include in the request,
                typically used for authentication (e.g., bearer tokens).
        timeout: Optional timeout for HTTP requests (default: 30.0 seconds).
        sse_read_timeout: Optional timeout for SSE connections (SSE only).
        terminate_on_close: Optional flag to terminate on connection close.
        httpx_client_factory: Optional factory for creating HTTP clients.
        auth: Optional httpx authentication for requests.
        __pre_validate_authentication: Optional flag to skip auth validation
                (default: True). Set to False for OAuth flows that require
                complex authentication flows.

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
    transport: NotRequired[str]  # Preferred field name
    type: NotRequired[str]  # Alternative field name for compatibility
    headers: NotRequired[dict[str, str] | None]
    timeout: NotRequired[float]
    sse_read_timeout: NotRequired[float]
    terminate_on_close: NotRequired[bool]
    httpx_client_factory: NotRequired[McpHttpClientFactory]
    auth: NotRequired[httpx.Auth]
    __prevalidate_authentication: NotRequired[bool]

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


# Type alias for bidirectional communication channels with MCP servers
# Note: This type is not officially exported by mcp.types but represents
# the standard transport interface used by all MCP client implementations
Transport: TypeAlias = tuple[
    MemoryObjectReceiveStream[mcp_types.JSONRPCMessage | Exception],
    MemoryObjectSendStream[mcp_types.JSONRPCMessage]
]


async def _connect_to_mcp_server(
    server_name: str,
    server_config: SingleMcpServerConfig,
    exit_stack: AsyncExitStack,
    logger: logging.Logger = logging.getLogger(__name__)
) -> Transport:
    """Establishes a connection to an MCP server with robust error handling.

    Implements consistent transport selection logic and includes authentication
    pre-validation to prevent async generator cleanup bugs in the MCP client library.
    
    Transport Selection Priority:
    1. Explicit transport/type field (must match URL protocol if URL provided)
    2. URL protocol auto-detection (http/https → StreamableHTTP, ws/wss → WebSocket)
    3. Command presence → Stdio transport
    4. Error if none of the above match
    
    For HTTP URLs without explicit transport, follows MCP specification backwards
    compatibility: try Streamable HTTP first, fallback to SSE on 4xx errors.
    
    Authentication Pre-validation:
    For HTTP/HTTPS servers, authentication is pre-validated before attempting
    the actual MCP connection to avoid async generator cleanup issues that can
    occur in the underlying MCP client library when authentication fails.

    Supports multiple transport types:
    - stdio: For local command-based servers
    - streamable_http, http: For Streamable HTTP servers
    - sse: For Server-Sent Events HTTP servers (legacy)
    - websocket, ws: For WebSocket servers

    Args:
        server_name: Server instance name to use for better logging and error context
        server_config: Configuration dictionary for server setup
        exit_stack: AsyncExitStack for managing transport lifecycle and cleanup
        logger: Logger instance for debugging and monitoring

    Returns:
        A Transport tuple containing receive and send streams for server communication

    Raises:
        McpInitializationError: If configuration is invalid or server initialization fails
        Exception: If unexpected errors occur during connection
    """
    try:
        logger.info(f'MCP server "{server_name}": '
                    f"initializing with: {server_config}")

        # Validate configuration first
        _validate_mcp_server_config(server_name, server_config, logger)
        
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
                if url_config.get("__pre_validate_authentication", True):
                    # Pre-validate authentication to avoid MCP async generator cleanup bugs
                    logger.info(f'MCP server "{server_name}": Pre-validating authentication')
                    auth_valid, auth_message = await _validate_auth_before_connection(
                        url_str,
                        headers=headers,
                        timeout=timeout or 30.0,
                        auth=auth,
                        logger=logger,
                        server_name=server_name
                    )

                    if not auth_valid:
                        # logger.error(f'MCP server "{server_name}": {auth_message}')
                        raise McpInitializationError(auth_message, server_name=server_name)

                # Now proceed with the original connection logic
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
                                  f"Using SSE transport (deprecated as of MCP 2025-03-26), consider migrating to streamable_http")
                    
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
                        
                        supports_streamable = await _test_streamable_http_support(
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
                                          f"Using SSE transport (deprecated as of MCP 2025-03-26), server should support Streamable HTTP")
                            
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
                raise McpInitializationError(
                    f'Unsupported URL scheme "{url_scheme}". '
                    f'Supported schemes: http/https (for streamable_http/sse), ws/wss (for websocket)',
                    server_name=server_name
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
            raise McpInitializationError(
                'Invalid configuration - '
                'either "url" or "command" must be specified',
                server_name=server_name
            )
            
    except Exception as e:
        logger.error(f'MCP server "{server_name}": error during initialization: {str(e)}')
        raise

    return transport


async def _get_mcp_server_tools(
    server_name: str,
    transport: Transport,
    exit_stack: AsyncExitStack,
    logger: logging.Logger = logging.getLogger(__name__)
) -> list[BaseTool]:
    """Retrieves and converts MCP server tools to LangChain BaseTool format.
    
    Establishes a client session with the MCP server, lists available tools,
    and wraps each tool in a LangChain-compatible adapter class. The adapter
    handles async execution, error handling, and result formatting.
    
    Tool Conversion Features:
    - JSON Schema to Pydantic model conversion for argument validation
    - Async-only execution (raises NotImplementedError for sync calls)
    - Automatic result formatting from MCP TextContent to strings
    - Error handling with ToolException for MCP tool failures
    - Comprehensive logging of tool input/output and execution metrics

    Args:
        server_name: Server instance name for logging and error context
        transport: Communication channels tuple (2-tuple for SSE/stdio, 3-tuple for streamable HTTP)
        exit_stack: AsyncExitStack for managing session lifecycle and cleanup
        logger: Logger instance for debugging and monitoring

    Returns:
        List of LangChain BaseTool instances that wrap MCP server tools

    Raises:
        McpInitializationError: If transport format is unexpected or session initialization fails
        Exception: If tool retrieval or conversion fails
    """
    try:
        # Handle both 2-tuple (SSE, stdio) and 3-tuple (streamable HTTP) returns
        # Third element in streamable HTTP contains session info/metadata
        if len(transport) == 2:
            read, write = transport
        elif len(transport) == 3:
            read, write, _ = transport  # Third element is session info/metadata
        else:
            raise McpInitializationError(
                f"Unexpected transport tuple length: {len(transport)}",
                server_name=server_name
            )

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
            adapter = create_mcp_langchain_adapter(tool, session, server_name, logger)
            langchain_tools.append(adapter)

        # Log available tools for debugging
        logger.info(f'MCP server "{server_name}": {len(langchain_tools)} '
                    f"tool(s) available:")
        for tool in langchain_tools:
            logger.info(f"- {tool.name}")
    except Exception as e:
        logger.error(f"Error getting MCP tools: {str(e)}")
        raise

    return langchain_tools


# Type hint for cleanup function
McpServerCleanupFn = Callable[[], Awaitable[None]]
"""Type for the async cleanup function returned by convert_mcp_to_langchain_tools.

This function encapsulates the cleanup of all MCP server connections managed by
the AsyncExitStack. When called, it properly closes all transport connections,
sessions, and resources in the correct order.

Important: Always call this function when you're done using the tools to prevent
resource leaks and ensure graceful shutdown of MCP server connections.

Example usage:
    tools, cleanup = await convert_mcp_to_langchain_tools(server_configs)
    try:
        # Use tools with your LangChain application...
        result = await tools[0].arun(param="value")
    finally:
        # Always cleanup, even if exceptions occur
        await cleanup()
"""


def _init_logger(log_level=logging.INFO) -> logging.Logger:
    """Creates a simple pre-configured logger.

    Returns:
        A configured Logger instance
    """
    logging.basicConfig(
        level=logging.INFO,  # More reasonable default level
        format="\x1b[90m[%(levelname)s]\x1b[0m %(message)s"
    )
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # Keep HTTP libraries quieter
    for lib in ["httpx", "urllib3", "requests", "anthropic", "openai"]:
        logging.getLogger(lib).setLevel(logging.WARNING)
    
    return logger


async def convert_mcp_to_langchain_tools(
    server_configs: McpServersConfig,
    logger: logging.Logger | int | None = None
) -> tuple[list[BaseTool], McpServerCleanupFn]:
    """Initialize multiple MCP servers and convert their tools to LangChain format.

    This is the main entry point for the library. It orchestrates the complete
    lifecycle of multiple MCP server connections, from initialization through
    tool conversion to cleanup. Provides robust error handling and authentication
    pre-validation to prevent common MCP client library issues.

    Key Features:
    - Parallel initialization of multiple servers for efficiency
    - Authentication pre-validation for HTTP servers to prevent async generator bugs
    - Automatic transport selection and fallback per MCP specification
    - Comprehensive error handling with McpInitializationError
    - User-controlled cleanup via returned async function
    - Support for both local (stdio) and remote (HTTP/WebSocket) servers

    Transport Support:
    - stdio: Local command-based servers (npx, uvx, python, etc.)
    - streamable_http: Modern HTTP servers (recommended, tried first)
    - sse: Legacy Server-Sent Events HTTP servers (fallback)
    - websocket: WebSocket servers for real-time communication

    Error Handling:
    All configuration and connection errors are wrapped in McpInitializationError
    with server context for easy debugging. Authentication failures are detected
    early to prevent async generator cleanup issues in the MCP client library.

    Args:
        server_configs: Dictionary mapping server names to configurations.
            Each config can be either McpServerCommandBasedConfig for local
            servers or McpServerUrlBasedConfig for remote servers.
        logger: Optional logger instance. If None, creates a pre-configured
            logger with appropriate levels for MCP debugging.
            If a logging level (e.g., `logging.DEBUG`), the pre-configured
            logger will be initialized with that level.

    Returns:
        A tuple containing:
        - List[BaseTool]: All tools from all servers, ready for LangChain use
        - McpServerCleanupFn: Async function to properly shutdown all connections

    Raises:
        McpInitializationError: If any server fails to initialize with detailed context

    Example:
        server_configs = {
            "local-filesystem": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "."]
            },
            "remote-api": {
                "url": "https://api.example.com/mcp",
                "headers": {"Authorization": "Bearer your-token"},
                "timeout": 30.0
            }
        }

        try:
            tools, cleanup = await convert_mcp_to_langchain_tools(server_configs)
            
            # Use tools with your LangChain application
            for tool in tools:
                result = await tool.arun(**tool_args)
                
        except McpInitializationError as e:
            print(f"Failed to initialize MCP server '{e.server_name}': {e}")
            
        finally:
            # Always cleanup when done
            await cleanup()
    """

    if logger is None:
        logger = logging.getLogger(__name__)
        # Check if the root logger has handlers configured
        if not logging.root.handlers and not logger.handlers:
            # No logging configured, use a simple pre-configured logger
            logger = _init_logger()
    elif isinstance(logger, int):
        # logger is actually a level like logging.DEBUG
        logger = _init_logger(log_level=logger)
    elif isinstance(logger, logging.Logger):
        # already a logger, use as is
        pass
    else:
        raise TypeError(
            "logger must be a logging.Logger, int (log level), or None"
        )

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
        transport = await _connect_to_mcp_server(
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
        tools = await _get_mcp_server_tools(
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
