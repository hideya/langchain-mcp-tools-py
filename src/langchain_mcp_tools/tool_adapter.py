"""MCP to LangChain tool adapter classes.

This module contains the adapter class that converts MCP tools to LangChain
BaseTool format, handling async execution, error handling, and result formatting.
"""

import logging
from typing import Any, NoReturn

try:
    from jsonschema_pydantic import jsonschema_to_pydantic  # type: ignore
    from langchain_core.tools import BaseTool, ToolException
    from mcp import ClientSession
    import mcp.types as mcp_types
    from pydantic import BaseModel
except ImportError as e:
    print(f"\nError: Required package not found: {e}")
    print("Please ensure all required packages are installed\n")
    import sys
    sys.exit(1)


def _fix_schema(schema: dict) -> dict:
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
            schema[key] = _fix_schema(value)  # Apply recursively
    return schema


def create_mcp_langchain_adapter(
    tool: mcp_types.Tool,
    session: ClientSession,
    server_name: str,
    logger: logging.Logger
) -> BaseTool:
    """Creates a LangChain tool adapter for an MCP tool.
    
    This function creates a LangChain-compatible tool that wraps an MCP tool,
    handling async execution, error handling, and result formatting.
    
    Args:
        tool: The MCP tool to wrap
        session: The MCP client session for tool execution
        server_name: Server name for logging context
        logger: Logger instance for debugging and monitoring
        
    Returns:
        A LangChain BaseTool instance that wraps the MCP tool
    """
    
    # Create local variable to work around Python scoping:
    # class definitions can access enclosing function locals but not
    # parameters directly
    client_session = session
    
    class McpToLangChainAdapter(BaseTool):
        """Adapter class to convert MCP tool to LangChain format.
        
        This adapter handles the conversion between MCP's async tool interface
        and LangChain's tool format, including argument validation, execution,
        and result formatting.
        
        Features:
        - JSON Schema to Pydantic model conversion for argument validation
        - Async-only execution (raises NotImplementedError for sync calls)
        - Automatic result formatting from MCP TextContent to strings
        - Error handling with ToolException for MCP tool failures
        - Comprehensive logging of tool input/output and execution metrics
        """
        name: str = tool.name or "NO NAME"
        description: str = tool.description or ""
        # Convert JSON schema to Pydantic model for argument validation
        args_schema: type[BaseModel] = jsonschema_to_pydantic(
            _fix_schema(tool.inputSchema)  # Apply schema conversion
        )
        session: ClientSession = client_session

        def _run(self, **kwargs: Any) -> NoReturn:
            """Synchronous execution is not supported for MCP tools.
            
            MCP tools are inherently async, so this method always raises
            NotImplementedError to direct users to use the async version.
            
            Raises:
                NotImplementedError: Always, as MCP tools only support async operations
            """
            raise NotImplementedError(
                "MCP tools only support async operations"
            )

        async def _arun(self, **kwargs: Any) -> Any:
            """Asynchronously executes the tool with given arguments.

            This method handles the actual execution of the MCP tool, including
            logging, error handling, and result formatting. It converts MCP's
            response format to LangChain's expected string format.

            Args:
                **kwargs: Arguments to be passed to the MCP tool

            Returns:
                Formatted response from the MCP tool as a string

            Raises:
                ToolException: If the tool execution fails
            """
            logger.info(f'MCP tool "{server_name}"/"{self.name}" '
                        f"received input: {kwargs}")

            try:
                # Filter out None values for optional parameters
                # LangChain 1.2.x started passing all parameters from the schema to the tool,
                # including optional ones with None values
                # MCP servers expect optional params to be omitted, not sent as null
                filtered_kwargs = {k: v for k, v in kwargs.items() if v is not None}
                result = await self.session.call_tool(self.name, filtered_kwargs)

                # Check for MCP tool execution errors
                if hasattr(result, "isError") and result.isError:
                    raise ToolException(
                        f"Tool execution failed: {result.content}"
                    )

                if not hasattr(result, "content"):
                    return str(result)

                # Convert MCP TextContent items to string format
                # The library uses LangChain's `response_format: 'content'` (the default),
                # which only supports text strings and BaseTool._arun() expects string return type
                try:
                    result_content_text = "\n\n".join(
                        item.text
                        for item in result.content
                        if isinstance(item, mcp_types.TextContent)
                    )
                    # Alternative approach using JSON serialization (preserved for reference):
                    # text_items = [
                    #     item
                    #     for item in result.content
                    #     if isinstance(item, mcp_types.TextContent)
                    # ]
                    # result_content_text = to_json(text_items).decode()

                except KeyError as e:
                    result_content_text = (
                        f"Error in parsing result.content: {str(e)}; "
                        f"contents: {repr(result.content)}"
                    )

                # Log rough result size for monitoring
                size = len(result_content_text.encode())
                logger.info(f'MCP tool "{server_name}"/"{self.name}" '
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
                    f'MCP tool "{server_name}"/"{self.name}" '
                    f"caused error:  {str(e)}"
                )
                if self.handle_tool_error:
                    return f"Error executing MCP tool: {str(e)}"
                raise

    return McpToLangChainAdapter()
