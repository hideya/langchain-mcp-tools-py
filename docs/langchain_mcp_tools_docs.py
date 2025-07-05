# Documentation-only version with simplified code
import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional, TextIO, Tuple, TypedDict, Union, NotRequired

# Import for forward reference
try:
    from langchain_core.tools import BaseTool
except ImportError:
    # For documentation only - create a placeholder if import fails
    class BaseTool:
        """Placeholder for LangChain BaseTool."""
        pass


class McpInitializationError(Exception):
    """Raised when MCP server initialization fails.
    
    This exception is raised when there are issues during MCP server setup,
    connection, or configuration validation. It includes the server name
    for better error context and debugging.
    
    Args:
        message: Description of the initialization error
        server_name: Optional name of the MCP server that failed
    """
    
    def __init__(self, message: str, server_name: Optional[str] = None):
        self.server_name = server_name
        super().__init__(message)
    
    def __str__(self) -> str:
        if self.server_name:
            return f'MCP server "{self.server_name}": {super().__str__()}'
        return super().__str__()


# Type definitions for public API
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

    Example::

        {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "."],
            "env": {"NODE_ENV": "production"},
            "cwd": "/path/to/working/directory",
            "errlog": open("server.log", "w")
        }
    """
    command: str
    args: NotRequired[List[str] | None]
    env: NotRequired[Dict[str, str] | None]
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

    Example for auto-detection (recommended)::

        {
            "url": "https://api.example.com/mcp",
            # Auto-tries Streamable HTTP first, falls back to SSE on 4xx
            "headers": {"Authorization": "Bearer token123"},
            "timeout": 60.0
        }

    Example for explicit Streamable HTTP::

        {
            "url": "https://api.example.com/mcp",
            "transport": "streamable_http",
            "headers": {"Authorization": "Bearer token123"},
            "timeout": 60.0
        }

    Example for explicit SSE (legacy)::

        {
            "url": "https://example.com/mcp/sse",
            "transport": "sse",
            "headers": {"Authorization": "Bearer token123"}
        }

    Example for WebSocket::

        {
            "url": "wss://example.com/mcp/ws",
            "transport": "websocket"
        }
    """
    url: str
    transport: NotRequired[str]  # Preferred field name
    type: NotRequired[str]  # Alternative field name for compatibility
    headers: NotRequired[Dict[str, str] | None]
    timeout: NotRequired[float]
    sse_read_timeout: NotRequired[float]
    terminate_on_close: NotRequired[bool]
    httpx_client_factory: NotRequired[Any]  # McpHttpClientFactory
    auth: NotRequired[Any]  # httpx.Auth
    __prevalidate_authentication: NotRequired[bool]


# Type for a single MCP server configuration, which can be either command-based or URL-based.
SingleMcpServerConfig = Union[McpServerCommandBasedConfig, McpServerUrlBasedConfig]
"""Configuration for a single MCP server, either command-based or URL-based.

This type represents the configuration for a single MCP server, which can be either:

1. A local server launched via command line (McpServerCommandBasedConfig)
2. A remote server accessed via URL (McpServerUrlBasedConfig)

The type is determined by the presence of either the "command" key (for command-based)
or the "url" key (for URL-based).
"""

# Configuration dictionary for multiple MCP servers
McpServersConfig = Dict[str, SingleMcpServerConfig]
"""Configuration dictionary for multiple MCP servers.

A dictionary mapping server names (as strings) to their respective configurations.
Each server name acts as a logical identifier used for logging and debugging.
The configuration for each server can be either command-based or URL-based.

Example::

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


# Type hint for cleanup function
McpServerCleanupFn = Callable[[], Awaitable[None]]
"""Type for the async cleanup function returned by convert_mcp_to_langchain_tools.

This function encapsulates the cleanup of all MCP server connections managed by
the AsyncExitStack. When called, it properly closes all transport connections,
sessions, and resources in the correct order.

Important: Always call this function when you're done using the tools to prevent
resource leaks and ensure graceful shutdown of MCP server connections.

Example usage::

    tools, cleanup = await convert_mcp_to_langchain_tools(server_configs)
    try:
        # Use tools with your LangChain application...
        result = await tools[0].arun(param="value")
    finally:
        # Always cleanup, even if exceptions occur
        await cleanup()
"""


async def convert_mcp_to_langchain_tools(
    server_configs: McpServersConfig,
    logger: Optional[logging.Logger] = None
) -> Tuple[List[BaseTool], McpServerCleanupFn]:
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

    Example::

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
    # This is just a documentation stub
    pass
