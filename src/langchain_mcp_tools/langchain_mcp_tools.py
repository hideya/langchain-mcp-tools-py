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
    """Determines if an error represents a 4xx HTTP status code or equivalent.
    
    Used to decide whether to fall back from Streamable HTTP to SSE transport
    per MCP specification. Also handles MCP protocol errors that indicate
    4xx-like conditions.
    
    Args:
        error: The error to check
        
    Returns:
        true if the error represents a 4xx HTTP status or equivalent
    """
    if not error:
        return False
    
    error_str = str(error).lower()
    
    # Check for explicit HTTP status codes
    if hasattr(error, 'status') and isinstance(error.status, int):
        return 400 <= error.status < 500
    
    # Check for httpx response errors
    if hasattr(error, 'response') and hasattr(error.response, 'status_code'):
        return 400 <= error.response.status_code < 500
    
    # Check for MCP protocol errors that indicate 4xx-like conditions
    if 'session terminated' in error_str:
        return True  # Often indicates server rejected the connection
    
    if 'method not found' in error_str or 'method not allowed' in error_str:
        return True  # Equivalent to 405 Method Not Allowed
        
    if 'not found' in error_str and '404' in error_str:
        return True  # Explicit 404
    
    # Check for error messages that typically indicate 4xx errors
    return (
        '4' in error_str and any(code in error_str for code in ['400', '401', '402', '403', '404', '405', '406', '407', '408', '409']) or
        'bad request' in error_str or
        'unauthorized' in error_str or
        'forbidden' in error_str or
        'not found' in error_str or
        'method not allowed' in error_str
    )

async def spawn_mcp_server_and_get_transport(
    server_name: str,
    server_config: SingleMcpServerConfig,
    exit_stack: AsyncExitStack,
    logger: logging.Logger = logging.getLogger(__name__)
) -> Transport:
    """Spawns an MCP server process and establishes communication channels.

    This function implements the MCP specification's backwards compatibility
    recommendation: for HTTP URLs, try Streamable HTTP first, then fallback to
    SSE on 4xx errors.

    Supports multiple transport types:
    - stdio: For local command-based servers
    - streamable_http: For Streamable HTTP servers (tried first for HTTP URLs)
    - sse: For Server-Sent Events HTTP servers (fallback for HTTP URLs)
    - websocket: For WebSocket servers

    Args:
        server_name: Server instance name to use for better logging
        server_config: Configuration dictionary for server setup
        exit_stack: Context manager for cleanup handling
        logger: Logger instance for debugging and monitoring

    Returns:
        A tuple of receive and send streams for server communication

    Raises:
        Exception: If server spawning fails
    """
    try:
        logger.info(f'MCP server "{server_name}": '
                    f"initializing with: {server_config}")

        # Check if this is a URL-based configuration
        url_str = str(server_config.get("url"))  # None becomes "None"
        
        if url_str != "None":  # URL-based configuration
            url_config = cast(McpServerUrlBasedConfig, server_config)
            url_scheme = urlparse(url_str).scheme
            transport_type = url_config.get("transport", "").lower()
            
            # Extract common parameters
            headers = url_config.get("headers", None)
            timeout = url_config.get("timeout", 30.0)
            auth = url_config.get("auth", None)
            
            if url_scheme in ("http", "https"):
                # HTTP/HTTPS: Apply MCP spec backwards compatibility logic
                
                if transport_type == "streamable_http":
                    # Explicit Streamable HTTP (no fallback)
                    logger.info(f'MCP server "{server_name}": '
                               f"connecting via Streamable HTTP (explicit) to {url_str}")
                    
                    kwargs = {}
                    if headers is not None:
                        kwargs["headers"] = headers
                    if timeout != 30.0:
                        kwargs["timeout"] = timeout
                    if auth is not None:
                        kwargs["auth"] = auth
                    
                    transport = await exit_stack.enter_async_context(
                        streamablehttp_client(url_str, **kwargs)
                    )
                    
                elif transport_type == "sse":
                    # Explicit SSE (no fallback)
                    logger.info(f'MCP server "{server_name}": '
                               f"connecting via SSE (explicit) to {url_str}")
                    logger.warning(f'MCP server "{server_name}": '
                                  f"SSE transport is deprecated, consider migrating to streamable_http")
                    
                    transport = await exit_stack.enter_async_context(
                        sse_client(url_str, headers=headers)
                    )
                    
                else:
                    # Auto-detection: Try Streamable HTTP first, fallback to SSE on 4xx
                    logger.debug(f'MCP server "{server_name}": '
                                f"attempting Streamable HTTP with SSE fallback")
                    
                    # First attempt: Streamable HTTP
                    try:
                        logger.info(f'MCP server "{server_name}": '
                                   f"trying Streamable HTTP to {url_str}")
                        
                        kwargs = {}
                        if headers is not None:
                            kwargs["headers"] = headers
                        if timeout != 30.0:
                            kwargs["timeout"] = timeout
                        if auth is not None:
                            kwargs["auth"] = auth
                        
                        transport = await exit_stack.enter_async_context(
                            streamablehttp_client(url_str, **kwargs)
                        )
                        
                        logger.info(f'MCP server "{server_name}": '
                                   f"successfully connected using Streamable HTTP")
                        
                    except Exception as error:
                        if is_4xx_error(error):
                            # Fallback to SSE on 4xx errors per MCP spec
                            logger.info(f'MCP server "{server_name}": '
                                       f"Streamable HTTP failed with 4xx error, falling back to SSE")
                            logger.warning(f'MCP server "{server_name}": '
                                          f"Using SSE fallback (deprecated), server should support Streamable HTTP")
                            
                            transport = await exit_stack.enter_async_context(
                                sse_client(url_str, headers=headers)
                            )
                            
                            logger.info(f'MCP server "{server_name}": '
                                       f"successfully connected using SSE fallback")
                        else:
                            # Re-throw non-4xx errors (network issues, etc.)
                            logger.error(f'MCP server "{server_name}": '
                                        f"Streamable HTTP failed with non-4xx error: {error}")
                            raise
                            
            elif url_scheme in ("ws", "wss"):
                # WebSocket transport
                logger.info(f'MCP server "{server_name}": '
                           f"connecting via WebSocket to {url_str}")
                
                transport = await exit_stack.enter_async_context(
                    websocket_client(url_str)
                )
                
            else:
                raise ValueError(
                    f'Unsupported URL scheme "{url_scheme}" for server "{server_name}". '
                    f'Supported URL schemes: http/https (for streamable_http/sse with auto-fallback), '
                    f'ws/wss (for websocket).'
                )
        
        else:
            # Command-based configuration (stdio transport)
            logger.info(f'MCP server "{server_name}": '
                       f"spawning local process via stdio")
            
            # NOTE: `uv` and `npx` seem to require PATH to be set.
            # To avoid confusion, it was decided to automatically append it
            # to the env if not explicitly set by the config.
            config = cast(McpServerCommandBasedConfig, server_config)
            # env = config.get("env", {}) does't work since it can yield None
            env_val = config.get("env")
            env = {} if env_val is None else dict(env_val)
            if "PATH" not in env:
                env["PATH"] = os.environ.get("PATH", "")

            # Use stdio client for commands
            # args = config.get("args", []) does't work since it can yield None
            args_val = config.get("args")
            args = [] if args_val is None else list(args_val)
            server_parameters = StdioServerParameters(
                command=config.get("command", ""),
                args=args,
                env=env,
                cwd=config.get("cwd", None)
            )

            # Initialize stdio client and register it with exit stack for
            # cleanup
            # NOTE: Why the key name `errlog` for `server_config` was chosen:
            # Unlike TypeScript SDK's `StdioServerParameters`, the Python
            # SDK's `StdioServerParameters` doesn't include `stderr: int`.
            # Instead, it calls `stdio_client()` with a separate argument
            # `errlog: TextIO`.  I once included `stderr: int` for
            # compatibility with the TypeScript version, but decided to
            # follow the Python SDK more closely.
            errlog_val = (cast(McpServerCommandBasedConfig, server_config)
                          .get("errlog"))
            kwargs = {"errlog": errlog_val} if errlog_val is not None else {}
            transport = await exit_stack.enter_async_context(
                stdio_client(server_parameters, **kwargs)
            )
    except Exception as e:
        logger.error(f"Error spawning MCP server: {str(e)}")
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
        level=logging.INFO,  # logging.DEBUG,
        format="\x1b[90m[%(levelname)s]\x1b[0m %(message)s"
    )
    return logging.getLogger()


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

    # Spawn all MCP servers concurrently
    for server_name, server_config in server_configs.items():
        # NOTE: the following `await` only blocks until the server subprocess
        # is spawned, i.e. after returning from the `await`, the spawned
        # subprocess starts its initialization independently of (so in
        # parallel with) the Python execution of the following lines.
        transport = await spawn_mcp_server_and_get_transport(
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
