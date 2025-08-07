# MCP to LangChain Tools Conversion Library / Python [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/hideya/langchain-mcp-tools-py/blob/main/LICENSE) [![pypi version](https://img.shields.io/pypi/v/langchain-mcp-tools.svg)](https://pypi.org/project/langchain-mcp-tools/) [![network dependents](https://dependents.info/hideya/langchain-mcp-tools-py/badge)](https://dependents.info/hideya/langchain-mcp-tools-py)

A simple, lightweight library to use 
[Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
server tools from LangChain.

<img width="500px" alt="langchain-mcp-tools-diagram" src="https://raw.githubusercontent.com/hideya/langchain-mcp-tools-py/refs/heads/main/docs/images/langchain-mcp-tools-diagram.png" />

Its simplicity and extra features for local MCP servers can make it useful as a basis for your own customizations.
However, it only supports text results of tool calls and does not support MCP features other than tools.

[LangChain's **official LangChain MCP Adapters** library](https://pypi.org/project/langchain-mcp-adapters/),
which supports comprehensive integration with LangChain, has been released.
You may want to consider using it if you don't have specific needs for this library.

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
    },
    "github": {
        "type": "http",
        "url": "https://api.githubcopilot.com/mcp/",
        "headers": {
            "Authorization": f"Bearer {os.environ.get('GITHUB_PERSONAL_ACCESS_TOKEN', '')}"
        }
    },
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
llm = init_chat_model("google_genai:gemini-2.5-flash")

# from langgraph.prebuilt import create_react_agent
agent = create_react_agent(
    llm,
    tools
)
```

A minimal but complete working usage example can be found
[in this example in the langchain-mcp-tools-py-usage repo](https://github.com/hideya/langchain-mcp-tools-py-usage/blob/main/src/example.py)

For hands-on experimentation with MCP server integration,
try [this MCP Client CLI tool built with this library](https://pypi.org/project/mcp-chat/)

A TypeScript equivalent of this utility is available
[here](https://www.npmjs.com/package/@h1deya/langchain-mcp-tools)

## Introduction

This package is intended to simplify the use of
[Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
server tools with LangChain / Python.

[Model Context Protocol (MCP)](https://modelcontextprotocol.io/) is the de facto industry standard
that dramatically expands the scope of LLMs by enabling the integration of external tools and resources,
including DBs, Cloud Storages, GitHub, Docker, Slack, and more.
There are quite a few useful MCP servers already available.
See [MCP Server Listing on the Official Site](https://github.com/modelcontextprotocol/servers?tab=readme-ov-file#model-context-protocol-servers).

This utility's goal is to make these numerous MCP servers easily accessible from LangChain.  
It contains a utility function `convert_mcp_to_langchain_tools()`.  
This async function handles parallel initialization of specified multiple MCP servers
and converts their available tools into a list of LangChain-compatible tools.

For detailed information on how to use this library, please refer to the following document:
["Supercharging LangChain: Integrating 2000+ MCP with ReAct"](https://medium.com/@h1deya/supercharging-langchain-integrating-450-mcp-with-react-d4e467cbf41a).

## MCP Protocol Support

This library supports **MCP Protocol version 2025-03-26** and maintains backwards compatibility with version 2024-11-05.
It follows the [official MCP specification](https://modelcontextprotocol.io/specification/2025-03-26/) for transport selection and backwards compatibility.

### Limitations

- **Tool Return Types**: Currently, only text results of tool calls are supported.
The library uses LangChain's `response_format: 'content'` (the default), which only supports text strings.
While MCP tools can return multiple content types (text, images, etc.), this library currently filters and uses only text content.
- **MCP Features**: Only MCP [Tools](https://modelcontextprotocol.io/docs/concepts/tools) are supported. Other MCP features like Resources, Prompts, and Sampling are not implemented.

### Note

- **Passing PATH Env Variable**: The library automatically adds the `PATH` environment variable to stdio server configrations if not explicitly provided to ensure servers can find required executables.

## API docs

Can be found [here](https://hideya.github.io/langchain-mcp-tools-py/)

## Building from Source

See [README_DEV.md](https://github.com/hideya/langchain-mcp-tools-py/blob/main/README_DEV.md) for details.

## Features

### stderr Redirection for Local MCP Server

A new key `"errlog"` has been introduced to specify a file-like object
to which local (stdio) MCP server's stderr is redirected.

```python
    log_path = f"mcp-server-{server_name}.log"
    log_file = open(log_path, "w")
    mcp_servers[server_name]["errlog"] = log_file
```

A usage example can be found [here](https://github.com/hideya/langchain-mcp-tools-py-usage/blob/3bd35d9fb49f4b631fe3d0cc8491d43cbf69693b/src/example.py#L88-L108).  
The key name `errlog` is derived from
[`stdio_client()`'s argument `errlog`](https://github.com/modelcontextprotocol/python-sdk/blob/babb477dffa33f46cdc886bc885eb1d521151430/src/mcp/client/stdio/__init__.py#L96).  

### Working Directory Configuration for Local MCP Servers

The working directory that is used when spawning a local (stdio) MCP server
can be specified with the `"cwd"` key as follows:

```python
    "local-server-name": {
        "command": "...",
        "args": [...],
        "cwd": "/working/directory"  # the working dir to be use by the server
    },
```

The key name `cwd` is derived from
Python SDK's [`StdioServerParameters`](https://github.com/modelcontextprotocol/python-sdk/blob/babb477dffa33f46cdc886bc885eb1d521151430/src/mcp/client/stdio/__init__.py#L76-L77).

### Transport Selection Priority

The library selects transports using the following priority order:

1. **Explicit transport/type field** (must match URL protocol if URL provided)
2. **URL protocol auto-detection** (http/https → StreamableHTTP → SSE, ws/wss → WebSocket)
3. **Command presence** → Stdio transport
4. **Error** if none of the above match

This ensures predictable behavior while allowing flexibility for different deployment scenarios.

### Remote MCP Server Support

`mcp_servers` configuration for Streamable HTTP, SSE (Server-Sent Events) and Websocket servers are as follows:

```py
    # Auto-detection: tries Streamable HTTP first, falls back to SSE on 4xx errors
    "auto-detect-server": {
       "url": f"http://{server_host}:{server_port}/..."
    },

    # Explicit Streamable HTTP
    "streamable-http-server": {
        "url": f"http://{server_host}:{server_port}/...",
        "transport": "streamable_http"
        # "type": "http"  # VSCode-style config also works instead of the above
    },

    # Explicit SSE
    "sse-server-name": {
        "url": f"http://{sse_server_host}:{sse_server_port}/...",
        "transport": "sse"  # or `"type": "sse"`
    },

    # WebSocket
    "ws-server-name": {
        "url": f"ws://${ws_server_host}:${ws_server_port}/..."
        # optionally `"transport": "ws"` or `"type": "ws"`
    },
```

The `"headers"` key can be used to pass HTTP headers to Streamable HTTP and SSE connection.  

```py
    "github": {
        "type": "http",
        "url": "https://api.githubcopilot.com/mcp/",
        "headers": {
            "Authorization": f"Bearer {os.environ.get('GITHUB_PERSONAL_ACCESS_TOKEN')}"
        }
    },
```

NOTE: When accessing the GitHub MCP server, [GitHub PAT (Personal Access Token)](https://github.com/settings/personal-access-tokens)
alone is not enough; your GitHub account must have an active Copilot subscription or be assigned a Copilot license through your organization.

**Auto-detection behavior (default):**
- For HTTP/HTTPS URLs without explicit `transport`, the library follows [MCP specification recommendations](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports#backwards-compatibility)
- First attempts Streamable HTTP transport
- If Streamable HTTP fails with a 4xx error, automatically falls back to SSE transport
- Non-4xx errors (network issues, etc.) are re-thrown without fallback

**Explicit transport selection:**
- Set `"transport": "streamable_http"` (or VSCode-style config `"type": "http"`) to force Streamable HTTP (no fallback)
- Set `"transport": "sse"` to force SSE transport
- WebSocket URLs (`ws://` or `wss://`) always use WebSocket transport

Streamable HTTP is the modern MCP transport that replaces the older HTTP+SSE transport. According to the [official MCP documentation](https://modelcontextprotocol.io/docs/concepts/transports): "SSE as a standalone transport is deprecated as of protocol version 2025-03-26. It has been replaced by Streamable HTTP, which incorporates SSE as an optional streaming mechanism."

### Authentication Support for Streamable HTTP Connections

The library supports OAuth 2.1 authentication for Streamable HTTP connections:

```py
from mcp.client.auth import OAuthClientProvider
...

    # Create OAuth authentication provider
    oauth_auth = OAuthClientProvider(
        server_url="https://...",
        client_metadata=...,
        storage=...,
        redirect_handler=...,
        callback_handler=...,
    )

    # Test configuration with OAuth auth
    mcp_servers = {
        "secure-streamable-server": {
            "url": "https://.../mcp/",
            // To avoid auto protocol fallback, specify the protocol explicitly when using authentication
            "transport": "streamable_http",  // or `"type": "http",`
            "auth": oauth_auth,
            "timeout": 30.0
        },
    }
```

Test implementations are provided:

- **Streamable HTTP Authentication Tests**:
  - MCP client uses this library: [streamable_http_oauth_test_client.py](https://github.com/hideya/langchain-mcp-tools-py/tree/main/testfiles/streamable_http_oauth_test_client.py)
  - Test MCP Server:  [streamable_http_oauth_test_server.py](https://github.com/hideya/langchain-mcp-tools-py/tree/main/testfiles/streamable_http_oauth_test_server.py)

### Authentication Support for SSE Connections (Legacy)

The library also supports authentication for SSE connections to MCP servers.
Note that SSE transport is deprecated; Streamable HTTP is the recommended approach.

## Change Log

Can be found [here](https://github.com/hideya/langchain-mcp-tools-py/blob/main/CHANGELOG.md)

## Appendix

### Troubleshooting

1. **Enable debug logging**: Set the log level to DEBUG to see detailed connection and execution logs:  

    ```
    tools, cleanup = await convert_mcp_to_langchain_tools(
        mcp_servers,
        logging.DEBUG
    )
    ```
2. **Check server errlog**: For stdio MCP servers, use `errlog` redirection to capture server error output
3. **Test explicit transports**: Try forcing specific transport types to isolate auto-detection issues
4. **Verify server independently**: Refer to [Debugging Section in MCP documentation](https://modelcontextprotocol.io/docs/tools/debugging)

### Troubleshooting Authentication Issues

When authentication errors occur, they often generate massive logs that make it difficult to identify that authentication is the root cause.

To address this problem, this library performs authentication pre-validation for HTTP/HTTPS MCP servers before attempting the actual MCP connection.
This ensures that clear error messages like `Authentication failed (401 Unauthorized)` or `Authentication failed (403 Forbidden)` appear at the end of the logs, rather than being buried in the middle of extensive error output.

**Important:** This pre-validation is specific to this library and not part of the official MCP specification.
In rare cases, it may interfere with certain MCP server behaviors.

#### When and How to Disable Pre-validation
Set `"__pre_validate_authentication": False` in your server config if:
- Using OAuth flows that require complex authentication handshakes
- The MCP server doesn't accept simple HTTP POST requests for validation
- You're experiencing false negatives in the auth validation

**Example:**
```python
"oauth-server": {
    "url": "https://api.example.com/mcp/",
    "auth": oauth_provider,  # Complex OAuth provider
    "__pre_validate_authentication": False  # Skip the pre-validation
}
```

### Debugging Authentication
1. **Check your tokens/credentials** - Most auth failures are due to expired or incorrect tokens
2. **Verify token permissions** - Some MCP servers require specific scopes (e.g., GitHub Copilot license)
3. **Test with curl** - Try a simple HTTP request to verify your auth setup:

   ```bash
   curl -H "Authorization: Bearer your-token" https://api.example.com/mcp/
   ```

### Resource Management

The returned `cleanup` function properly handles resource cleanup:

- Closes all MCP server connections concurrently
- Logs any cleanup failures
- Continues cleanup of remaining servers even if some fail
- Should always be called when done using the tools

```python
try:
    tools, cleanup = await convert_mcp_to_langchain_tools(mcp_servers)

    # Use tools with your LLM

finally:
    # cleanup can be undefined when an exeption occurs during initialization
    if "cleanup" in locals():
        await cleanup()
```

### For Developers

See [TECHNICAL.md](TECHNICAL.md) for technical details about implementation challenges and solutions.
