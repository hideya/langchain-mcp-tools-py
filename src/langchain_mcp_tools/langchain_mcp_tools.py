# Standard library imports
from anyio.streams.memory import (
    MemoryObjectReceiveStream,
    MemoryObjectSendStream,
)
import logging
import os
import sys
from contextlib import AsyncExitStack, asynccontextmanager
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    NoReturn,
    Optional,
    Tuple,
    Type,
    TypeAlias,
)

# Third-party imports
try:
    from jsonschema_pydantic import jsonschema_to_pydantic  # type: ignore
    from langchain_core.tools import BaseTool, ToolException
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client, StdioServerParameters
    import mcp.types as mcp_types
    from pydantic import BaseModel
    # from pydantic_core import to_json
except ImportError as e:
    print(f'\nError: Required package not found: {e}')
    print('Please ensure all required packages are installed\n')
    sys.exit(1)


def fix_schema(schema: dict) -> dict:
    """Converts JSON Schema 'type': ['string', 'null'] to 'anyOf' format"""
    if isinstance(schema, dict):
        if 'type' in schema and isinstance(schema['type'], list):
            schema['anyOf'] = [{'type': t} for t in schema['type']]
            del schema['type']  # Remove 'type' and standardize to 'anyOf'
        for key, value in schema.items():
            schema[key] = fix_schema(value)  # Apply recursively
    return schema


# Type alias for the bidirectional communication channels with the MCP server
# FIXME: not defined in mcp.types, really?
StdioTransport: TypeAlias = tuple[
    MemoryObjectReceiveStream[mcp_types.JSONRPCMessage | Exception],
    MemoryObjectSendStream[mcp_types.JSONRPCMessage]
]


async def spawn_mcp_server_and_get_transport(
    server_name: str,
    server_config: Dict[str, Any],
    exit_stack: AsyncExitStack,
    logger: logging.Logger = logging.getLogger(__name__)
) -> StdioTransport:
    """
    Spawns an MCP server process and establishes communication channels.

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
                    f'initializing with: {server_config}')

        # NOTE: `uv` and `npx` seem to require PATH to be set.
        # To avoid confusion, it was decided to automatically append it
        # to the env if not explicitly set by the config.
        env = dict(server_config.get('env', {}))
        if 'PATH' not in env:
            env['PATH'] = os.environ.get('PATH', '')

        # Create server parameters with command, arguments and environment
        server_params = StdioServerParameters(
            command=server_config['command'],
            args=server_config.get('args', []),
            env=env,
            cwd=server_config.get('cwd', None)
        )

        # Initialize stdio client and register it with exit stack for cleanup
        # NOTE: Why the key name `stderr` for `server_config` was chosen:
        # Unlike the TypeScript SDK's `StdioServerParameters`, the Python SDK's
        # `StdioServerParameters` doesn't include `stderr`.
        # Instead, it calls `stdio_client()` with a separate argument
        # `errlog`.  I once thought of using `errlog` for the key for the
        # Pyhton version, but decided to follow the TypeScript version since
        # its public API already exposes the key name and I choose consistency.
        stdio_transport = await exit_stack.enter_async_context(
            stdio_client(
                server_params,
                errlog=server_config.get('stderr', None)
            )
        )
    except Exception as e:
        logger.error(f'Error spawning MCP server: {str(e)}')
        raise

    return stdio_transport


async def get_mcp_server_tools(
    server_name: str,
    stdio_transport: StdioTransport,
    exit_stack: AsyncExitStack,
    logger: logging.Logger = logging.getLogger(__name__)
) -> List[BaseTool]:
    """
    Retrieves and converts MCP server tools to LangChain format.

    Args:
        server_name: Server instance name to use for better logging
        stdio_transport: Communication channels tuple
        exit_stack: Context manager for cleanup handling
        logger: Logger instance for debugging and monitoring

    Returns:
        List of LangChain tools converted from MCP tools

    Raises:
        Exception: If tool conversion fails
    """
    try:
        read, write = stdio_transport

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
        langchain_tools: List[BaseTool] = []
        for tool in tools_response.tools:

            # Define adapter class to convert MCP tool to LangChain format
            class McpToLangChainAdapter(BaseTool):
                name: str = tool.name or 'NO NAME'
                description: str = tool.description or ''
                # Convert JSON schema to Pydantic model for argument validation
                args_schema: Type[BaseModel] = jsonschema_to_pydantic(
                    fix_schema(tool.inputSchema)  # Apply schema conversion
                )
                session: Optional[ClientSession] = None

                def _run(self, **kwargs: Any) -> NoReturn:
                    raise NotImplementedError(
                        'MCP tools only support async operations'
                    )

                async def _arun(self, **kwargs: Any) -> Any:
                    """
                    Asynchronously executes the tool with given arguments.
                    Logs input/output and handles errors.
                    """
                    logger.info(f'MCP tool "{server_name}"/"{tool.name}" '
                                f'received input: {kwargs}')

                    try:
                        result = await session.call_tool(self.name, kwargs)

                        if hasattr(result, 'isError') and result.isError:
                            raise ToolException(
                                f'Tool execution failed: {result.content}'
                            )

                        if not hasattr(result, 'content'):
                            return str(result)

                        # The return type of `BaseTool`'s `arun` is `str`.
                        try:
                            result_content_text = '\n\n'.join(
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
                                f'Error in parsing result.content: {str(e)}; '
                                f'contents: {repr(result.content)}'
                            )

                        # Log rough result size for monitoring
                        size = len(result_content_text.encode())
                        logger.info(f'MCP tool "{server_name}"/"{tool.name}" '
                                    f'received result (size: {size})')

                        # If no text content, return a clear message
                        # describing the situation.
                        result_content_text = (
                            result_content_text or
                            'No text content available in response'
                        )

                        return result_content_text

                    except Exception as e:
                        logger.warn(
                            f'MCP tool "{server_name}"/"{tool.name}" '
                            f'caused error:  {str(e)}'
                        )
                        if self.handle_tool_error:
                            return f'Error executing MCP tool: {str(e)}'
                        raise

            langchain_tools.append(McpToLangChainAdapter())

        # Log available tools for debugging
        logger.info(f'MCP server "{server_name}": {len(langchain_tools)} '
                    f'tool(s) available:')
        for tool in langchain_tools:
            logger.info(f'- {tool.name}')
    except Exception as e:
        logger.error(f'Error getting MCP tools: {str(e)}')
        raise

    return langchain_tools


# A very simple pre-configured logger for fallback
def init_logger() -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,  # logging.DEBUG,
        format='\x1b[90m[%(levelname)s]\x1b[0m %(message)s'
    )
    return logging.getLogger()


# Type hint for cleanup function
McpServerCleanupFn = Callable[[], Awaitable[None]]


async def convert_mcp_to_langchain_tools(
    server_configs: Dict[str, Dict[str, Any]],
    logger: Optional[logging.Logger] = None
) -> Tuple[List[BaseTool], McpServerCleanupFn]:
    """Initialize multiple MCP servers and convert their tools to
    LangChain format.

    This async function manages parallel initialization of multiple MCP
    servers, converts their tools to LangChain format, and provides a cleanup
    mechanism. It orchestrates the full lifecycle of multiple servers.

    Args:
        server_configs: Dictionary mapping server names to their
            configurations, where each configuration contains command, args,
            and env settings
        logger: Logger instance to use for logging events and errors.
           If None, uses module logger with fallback to a pre-configured
           logger when no root handlers exist.

    Returns:
        A tuple containing:
            - List of converted LangChain tools from all servers
            - Async cleanup function to properly shutdown all server
                connections

    Example:
        server_configs = {
            'fetch': {
                'command': 'uvx', 'args': ['mcp-server-fetch']
            },
            'weather': {
                'command': 'npx', 'args': ['-y','@h1deya/mcp-server-weather']
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
    stdio_transports: List[StdioTransport] = []
    async_exit_stack = AsyncExitStack()

    # Spawn all MCP servers concurrently
    for server_name, server_config in server_configs.items():
        # NOTE: the following `await` only blocks until the server subprocess
        # is spawned, i.e. after returning from the `await`, the spawned
        # subprocess starts its initialization independently of (so in
        # parallel with) the Python execution of the following lines.
        stdio_transport = await spawn_mcp_server_and_get_transport(
            server_name,
            server_config,
            async_exit_stack,
            logger
        )
        stdio_transports.append(stdio_transport)

    # Convert tools from each server to LangChain format
    langchain_tools: List[BaseTool] = []
    for (server_name, server_config), stdio_transport in zip(
        server_configs.items(),
        stdio_transports,
        strict=True
    ):
        tools = await get_mcp_server_tools(
            server_name,
            stdio_transport,
            async_exit_stack,
            logger
        )
        langchain_tools.extend(tools)

    # Define a cleanup function to properly shut down all servers
    async def mcp_cleanup() -> None:
        """Closes all server connections and cleans up resources"""
        await async_exit_stack.aclose()

    # Log summary of initialized tools
    logger.info(f'MCP servers initialized: {len(langchain_tools)} tool(s) '
                f'available in total')
    for tool in langchain_tools:
        logger.debug(f'- {tool.name}')

    return langchain_tools, mcp_cleanup
