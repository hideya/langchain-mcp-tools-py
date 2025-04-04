# Standard library imports
import asyncio
import logging
import socket
import subprocess
import sys
import time
from contextlib import ExitStack

# Third-party imports
try:
    from dotenv import load_dotenv
    from langchain.chat_models import init_chat_model
    from langchain.schema import HumanMessage
    from langgraph.prebuilt import create_react_agent
except ImportError as e:
    print(f"\nError: Required package not found: {e}")
    print("Please ensure all required packages are installed\n")
    sys.exit(1)

# Local application imports
from langchain_mcp_tools import (
    convert_mcp_to_langchain_tools,
    McpServersConfig,
)


# A very simple logger
def init_logger() -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,  # logging.DEBUG,
        format="\x1b[90m%(levelname)s:\x1b[0m %(message)s"
    )
    return logging.getLogger()


async def run() -> None:
    load_dotenv()

    sse_server_process, sse_server_port = start_mcp_server(
        "SSE",  "npx -y @h1deya/mcp-server-weather")

    ws_server_process, ws_server_port = start_mcp_server(
        "WS",  "npx -y @h1deya/mcp-server-weather")

    try:
        mcp_servers: McpServersConfig = {
            "filesystem": {
                "command": "npx",
                "args": [
                    "-y",
                    "@modelcontextprotocol/server-filesystem",
                    "."  # path to a directory to allow access to
                ],
                "cwd": "/tmp"  # the working dir to be use by the server
            },
            "fetch": {
                "command": "uvx",
                "args": [
                    "mcp-server-fetch"
                ]
            },
            # "weather": {
            #     "command": "npx",
            #     "args": [
            #         "-y",
            #         "@h1deya/mcp-server-weather"
            #     ]
            # },
            # "weather": {
            #     "url": f"http://localhost:{sse_server_port}/sse"
            # },
            "weather": {
                "url": f"ws://localhost:{ws_server_port}/message"
            },
        }

        # Set a file-like object to which MCP server's stderr is redirected
        # NOTE: Why the key name `errlog` for `server_config` was chosen:
        # Unlike TypeScript SDK's `StdioServerParameters`, the Python
        # SDK's `StdioServerParameters` doesn't include `stderr: int`.
        # Instead, it calls `stdio_client()` with a separate argument
        # `errlog: TextIO`.  I once included `stderr: int` for
        # compatibility with the TypeScript version, but decided to
        # follow the Python SDK more closely.
        log_file_exit_stack = ExitStack()
        for server_name in mcp_servers:
            server_config = mcp_servers[server_name]
            # Skip URL-based servers (no command)
            if "command" not in server_config or not server_config["command"]:
                continue
            log_path = f"mcp-server-{server_name}.log"
            log_file = open(log_path, "w")
            server_config["errlog"] = log_file
            log_file_exit_stack.callback(log_file.close)

        tools, cleanup = await convert_mcp_to_langchain_tools(
            mcp_servers,
            # init_logger()
        )

        llm = init_chat_model(
            # model="claude-3-7-sonnet-latest",
            # model_provider="anthropic"
            model="o3-mini",
            model_provider="openai"
        )

        agent = create_react_agent(
            llm,
            tools
        )

        # query = "Read the news headlines on bbc.com"
        # query = "Read and briefly summarize the LICENSE file"
        # query = "Tell me the number of directories in the current directory"
        query = "Tomorrow's weather in SF?"

        print("\x1b[33m")  # color to yellow
        print(query)
        print("\x1b[0m")   # reset the color

        messages = [HumanMessage(content=query)]

        result = await agent.ainvoke({"messages": messages})

        result_messages = result["messages"]
        # the last message should be an AIMessage
        response = result_messages[-1].content

        print("\x1b[36m")  # color to cyan
        print(response)
        print("\x1b[0m")   # reset the color

    finally:
        if cleanup is not None:
            await cleanup()
        if "log_file_exit_stack" in locals():
            log_file_exit_stack.close()
        if "sse_server_process" in locals():
            sse_server_process.terminate()
        if "ws_server_process" in locals():
            ws_server_process.terminate()


def start_mcp_server(transport_type, mcp_server_run_command, wait_time=1):
    """
    Start an MCP server process via supergateway with the specified transport
    type.

    Args:
        transport_type (str): The transport type, either 'sse' or 'ws'
        mcp_server_package (str): The NPM package name for the MCP server
        wait_time (int): Time to wait for the server to start listening on its
        port

    Returns:
        tuple: (server_process, server_port)
    """
    def find_free_port():
        """Find and return a free port on localhost."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))  # Bind to a free port provided by the system
            return s.getsockname()[1]  # Return the port number assigned

    server_port = find_free_port()

    # Base command common to both server types
    command = [
        "npx",
        "-y",
        "supergateway",
        "--stdio",
        mcp_server_run_command,
        "--port", str(server_port),
        "--messagePath", "/message"
    ]

    # Add transport-specific arguments
    if transport_type.lower() == 'sse':
        command.extend([
            "--baseUrl", f"http://localhost:{server_port}",
            "--ssePath", "/sse"
        ])
    elif transport_type.lower() == 'ws':
        command.extend([
            "--outputTransport", "ws"
        ])
    else:
        raise ValueError(f"Unsupported transport type: {transport_type}")

    # Start the server process
    server_process = subprocess.Popen(
        command,
        stdout=sys.stdout,
        stderr=sys.stderr,
        text=True
    )

    print(f"Started {transport_type.upper()} MCP Server Process with PID:"
          f" {server_process.pid}")
    time.sleep(wait_time)  # wait until the server starts listening on the port

    return server_process, server_port


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
