
"""LangChain MCP Tools - Convert MCP servers to LangChain tools."""

try:
    from importlib.metadata import version
    __version__ = version("langchain_mcp_tools")
except ImportError:
    __version__ = "unknown"

from .langchain_mcp_tools import (
  convert_mcp_to_langchain_tools,
  McpServerCleanupFn,
  McpServersConfig,
  McpServerCommandBasedConfig,
  McpServerUrlBasedConfig,
  SingleMcpServerConfig,
)

from .transport_utils import (
  McpInitializationError,
)
