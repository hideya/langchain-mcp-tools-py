# Standard library imports
import asyncio
import logging
import sys
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

from test_mcp_server_sse import SseServerManager
from test_mcp_server_ws import WebSocketServerManager


# A very simple logger
def init_logger() -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,  # logging.DEBUG,
        format="\x1b[90m%(levelname)s:\x1b[0m %(message)s"
    )
    return logging.getLogger()


async def run() -> None:
    load_dotenv()

    sse_server_manager = SseServerManager()
    try:
        sse_server_port = sse_server_manager.spawn_server()
        print(f"SSE Server started on port: {sse_server_port}")
    except Exception as e:
        print("Ignoring ERROR durting starting SSE Server on port: "
              f"{sse_server_port}: ", e)

    ws_server_manager = WebSocketServerManager()
    try:
        ws_server_port = ws_server_manager.spawn_server()
        print(f"Websocket Server started on port: {ws_server_port}")
    except Exception as e:
        print("Ignoring ERROR durting starting Websocket Server on port: "
              f"{ws_server_port}: ", e)

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
            "weather": {
                "command": "npx",
                "args": [
                    "-y",
                    "@h1deya/mcp-server-weather"
                ]
            },
            "sse-test": {
                "url": f"http://127.0.0.1:{sse_server_port}/sse"
            },
            "ws-test": {
                "url": f"ws://127.0.0.1:{ws_server_port}/ws"
            },
        }

        # Set a file-like object to which MCP server's stderr is redirected
        # NOTE: Why the key name `errlog` for `server_config` was chosen:
        # Unlike the TypeScript SDK's `StdioServerParameters`, the Python
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
        # query = "Tomorrow's weather in SF?"
        # query = "Use the SSE test tool and tell me the result"
        query = "Use the WS test tool and tell me the result"

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
        if "sse_server_manager" in locals():
            sse_server_manager.terminate_server()
        if "ws_server_manager" in locals():
            ws_server_manager.terminate_server()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
