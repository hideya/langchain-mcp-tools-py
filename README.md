# MCP To LangChain Tools Conversion Utility [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/hideya/langchain-mcp-tools-py/blob/main/LICENSE) [![pypi version](https://img.shields.io/pypi/v/langchain-mcp-tools.svg)](https://pypi.org/project/langchain-mcp-tools/)

This package is intended to simplify the use of
[Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
server tools with LangChain / Python.

[Model Context Protocol (MCP)](https://modelcontextprotocol.io/),
an open source technology
[announced by Anthropic](https://www.anthropic.com/news/model-context-protocol),
dramatically expands LLM’s scope
by enabling external tool and resource integration, including
Google Drive, Slack, Notion, Spotify, Docker, PostgreSQL, and more…

Over 800 functional components available as MCP servers:

- [Glama’s list of Open-Source MCP servers](https://glama.ai/mcp/servers)
- [Smithery: MCP Server Registry](https://smithery.ai/)
- [awesome-mcp-servers](https://github.com/hideya/awesome-mcp-servers#Server-Implementations)
- [MCP Get Started/Example Servers](https://modelcontextprotocol.io/examples)

The goal of this utility is to make these 800+ MCP servers readily accessible from LangChain.

It contains a utility function `convert_mcp_to_langchain_tools()`.  
This async function handles parallel initialization of specified multiple MCP servers
and converts their available tools into a list of LangChain-compatible tools.

For detailed information on how to use this library, please refer to the following document:
- ["Supercharging LangChain: Integrating 800+ MCP with ReAct"](https://medium.com/@h1deya/supercharging-langchain-integrating-800-mcp-with-react-d4e467cbf41a)

A typescript equivalent of this utility is available
[here](https://www.npmjs.com/package/@h1deya/langchain-mcp-tools)

## Prerequisites

- Python 3.11+

## Installation

```bash
pip install langchain-mcp-tools
```

## Quick Start

`convert_mcp_to_langchain_tools()` utility function accepts MCP server configurations
that follow the same structure as
[Claude for Desktop](https://modelcontextprotocol.io/quickstart/user),
but only the contents of the `mcpServers` property,
and is expressed as a `dict`, e.g.:

```python
mcp_configs = {
    'filesystem': {
        'command': 'npx',
        'args': ['-y', '@modelcontextprotocol/server-filesystem', '.']
    },
    'fetch': {
        'command': 'uvx',
        'args': ['mcp-server-fetch']
    }
}

tools, cleanup = await convert_mcp_to_langchain_tools(
    mcp_configs
)
```

This utility function initializes all specified MCP servers in parallel,
and returns LangChain Tools
([`tools: List[BaseTool]`](https://python.langchain.com/api_reference/core/tools/langchain_core.tools.base.BaseTool.html#langchain_core.tools.base.BaseTool))
by gathering available MCP tools from the servers,
and by wrapping them into LangChain tools.
It also returns an async callback function (`cleanup: McpServerCleanupFn`)
to be invoked to close all MCP server sessions when finished.

The returned tools can be used with LangChain, e.g.:

```python
# from langchain.chat_models import init_chat_model
llm = init_chat_model(
    model='claude-3-5-sonnet-latest',
    model_provider='anthropic'
)

# from langgraph.prebuilt import create_react_agent
agent = create_react_agent(
    llm,
    tools
)
```

Find complete, minimal working usage examples
[here](https://github.com/hideya/langchain-mcp-tools-py-usage/blob/main/src/example.py)

For hands-on experimentation with MCP server integration,
try [this LangChain application built with the utility](https://github.com/hideya/mcp-client-langchain-py)

For detailed information on how to use this library, please refer to the following document:  
["Supercharging LangChain: Integrating 800+ MCP with ReAct"](https://medium.com/@h1deya/supercharging-langchain-integrating-800-mcp-with-react-d4e467cbf41a)

## Limitations

Currently, only text results of tool calls are supported.
