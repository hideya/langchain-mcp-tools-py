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

Over 2000 functional components available as MCP servers:

- [MCP Server Listing on the Official Site](https://github.com/modelcontextprotocol/servers?tab=readme-ov-file#model-context-protocol-servers)
- [MCP.so - Find Awesome MCP Servers and Clients](https://mcp.so/)
- [Smithery: MCP Server Registry](https://smithery.ai/)

The goal of this utility is to make these 2000+ MCP servers readily accessible from LangChain.

It contains a utility function `convert_mcp_to_langchain_tools()`.  
This async function handles parallel initialization of specified multiple MCP servers
and converts their available tools into a list of LangChain-compatible tools.

For detailed information on how to use this library, please refer to the following document:
- ["Supercharging LangChain: Integrating 2000+ MCP with ReAct"](https://medium.com/@h1deya/supercharging-langchain-integrating-450-mcp-with-react-d4e467cbf41a)

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
mcp_servers = {
    "filesystem": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "."]
    },
    "fetch": {
        "command": "uvx",
        "args": ["mcp-server-fetch"]
    }
}

tools, cleanup = await convert_mcp_to_langchain_tools(
    mcp_servers
)
```

This utility function initializes all specified MCP servers in parallel,
and returns LangChain Tools
([`tools: list[BaseTool]`](https://python.langchain.com/api_reference/core/tools/langchain_core.tools.base.BaseTool.html#langchain_core.tools.base.BaseTool))
by gathering available MCP tools from the servers,
and by wrapping them into LangChain tools.
It also returns an async callback function (`cleanup: McpServerCleanupFn`)
to be invoked to close all MCP server sessions when finished.

The returned tools can be used with LangChain, e.g.:

```python
# from langchain.chat_models import init_chat_model
llm = init_chat_model(
    model='claude-3-7-sonnet-latest',
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
["Supercharging LangChain: Integrating 2000+ MCP with ReAct"](https://medium.com/@h1deya/supercharging-langchain-integrating-450-mcp-with-react-d4e467cbf41a)

## Experimental Features

### Remote MCP Server Support

`mcp_servers` configuration for SSE and Websocket servers are as follows:

```python
    "sse-server-name": {
        "url": f"http://{sse_server_host}:{sse_server_port}/..."
    },

    "ws-server-name": {
        "url": f"ws://{ws_server_host}:{ws_server_port}/..."
    },
```

Note that the key name `"url"` may be changed in the future to match
the MCP server configurations used by Claude for Desktop once
it introduces remote server support.

### Working Directory Configuration for Local MCP Servers

The working directory that is used when spawning a local MCP server
can be specified with the `cwd` key as follows:

```python
    "local-server-name": {
        "command": "...",
        "args": [...],
        "cwd": "/working/directory"  # the working dir to be use by the server
    },
```

### Configuration for MCP Server stderr Redirection

A new key `errlog` has been introduced in to specify a file-like object
to which MCP server's stderr is redirected.

```python
    log_path = f"mcp-server-{server_name}.log"
    log_file = open(log_path, "w")
    mcp_servers[server_name]["errlog"] = log_file
```

**NOTE: Why the key name `errlog` for `server_config` was chosen:**  
Unlike TypeScript SDK's `StdioServerParameters`, the Python
SDK's `StdioServerParameters` doesn't include `stderr: int`.
Instead, it calls `stdio_client()` with a separate argument
`errlog: TextIO`.  I once included `stderr: int` for
compatibility with the TypeScript version, but decided to
follow the Python SDK more closely.

## Limitations

- Currently, only text results of tool calls are supported.
- Fatures other than [Tools](https://modelcontextprotocol.io/docs/concepts/tools) are not supported.

## Change Log

Can be found [here](https://github.com/hideya/langchain-mcp-tools-py/blob/main/CHANGELOG.md)
