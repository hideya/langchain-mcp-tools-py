# Standard library imports
import asyncio
import logging
import os
import sys
from contextlib import ExitStack

# Third-party imports
try:
    from dotenv import load_dotenv
    from langchain.chat_models import init_chat_model
    from langchain_core.messages import HumanMessage
    from langchain.agents import create_agent
except ImportError as e:
    print(f"\nError: Required package not found: {e}")
    print("Please ensure all required packages are installed\n")
    sys.exit(1)

# Local application imports
from langchain_mcp_tools import (
    convert_mcp_to_langchain_tools,
    McpServersConfig,
)

from remote_server_utils import start_remote_mcp_server_locally


# Run a SSE MCP server using Supergateway in a separate process
sse_server_process, sse_server_port = start_remote_mcp_server_locally(
    "SSE", "npx -y @h1deya/mcp-server-weather")

# Run a WS MCP server using Supergateway in a separate process
ws_server_process, ws_server_port = start_remote_mcp_server_locally(
    "WS", "npx -y @h1deya/mcp-server-weather")


async def run() -> None:
    load_dotenv()

    try:
        mcp_servers: McpServersConfig = {
            # # Run the weather MCP server locally for sanity check
            # "us-weather": {  # US weather only
            #     "command": "npx",
            #     "args": [
            #         "-y",
            #         "@h1deya/mcp-server-weather"
            #     ]
            # },

            # Auto-detection example
            # This will try Streamable HTTP first, then fallback to SSE
            "us-weather": {
                "url": f"http://localhost:{sse_server_port}/sse"
            },

            # "us-weather": {
            #     "url": f"http://localhost:{sse_server_port}/sse",
            #     "transport": "sse"  # Force SSE
            #     # "type": "sse"  # This also works instead of the above
            # },

            # "us-weather": {
            #     "url": f"ws://localhost:{ws_server_port}/message",
            #     # optionally `"transport": "ws"` or `"type": "ws"`
            # },
        }

        # MCP server's stderr redirection
        # Set a file-like object to which MCP server's stderr is redirected
        log_file_exit_stack = ExitStack()
        for server_name in mcp_servers:
            server_config = mcp_servers[server_name]
            # Skip URL-based servers (no command)
            if "command" not in server_config:
                continue
            log_path = f"mcp-server-{server_name}.log"
            log_file = open(log_path, "w")
            server_config["errlog"] = log_file
            log_file_exit_stack.callback(log_file.close)

        ### https://developers.openai.com/api/docs/pricing
        ### https://platform.openai.com/settings/organization/billing/overview
        model_name = "openai:gpt-5-mini"
        # model_name = "openai:gpt-5.2"

        ### https://platform.claude.com/docs/en/about-claude/models/overview
        ### https://console.anthropic.com/settings/billing
        # model_name = "anthropic:claude-3-5-haiku-latest"
        # model_name = "anthropic:claude-haiku-4-5"

        ### https://ai.google.dev/gemini-api/docs/pricing
        ### https://console.cloud.google.com/billing
        # model_name = "google_genai:gemini-2.5-flash"
        # model_name = "google_genai:gemini-3-flash-preview"

        ### https://docs.x.ai/developers/models
        # model_name = "xai:grok-3-mini"
        # model_name = "xai:grok-4-1-fast-non-reasoning"

        tools, cleanup = await convert_mcp_to_langchain_tools(
            mcp_servers,
            logging.DEBUG
        )

        model = init_chat_model(model_name)

        agent = create_agent(
            model,
            tools
        )

        print("\x1b[32m", end="")  # color to green
        print("\nLLM model:", getattr(model, 'model', getattr(model, 'model_name', 'unknown')))
        print("\x1b[0m", end="")  # reset the color

        query = "Are there any weather alerts in California?"

        print("\x1b[33m")  # color to yellow
        print(query)
        print("\x1b[0m")   # reset the color

        messages = [HumanMessage(content=query)]

        result = await agent.ainvoke({"messages": messages})

        result_messages = result["messages"]
        # the last message should be an AIMessage
        response_content = result_messages[-1].content

        # Handle both string and list content (for multimodal models)
        # NOTE: Gemini 3 preview returns a list content, even for a single text
        if isinstance(response_content, str):
            response = response_content
        elif isinstance(response_content, list):
            # Extract text from content blocks
            text_parts = []
            for block in response_content:
                if isinstance(block, dict) and "text" in block:
                    text_parts.append(block["text"])
                elif isinstance(block, str):
                    text_parts.append(block)
                elif hasattr(block, "text"):
                    text_parts.append(block.text)
            response = " ".join(text_parts) if text_parts else ""
            print(response)
        else:
            raise TypeError(
                f"Unexpected response content type: {type(response_content)}"
            )

        print("\x1b[36m")  # color to cyan
        print(response)
        print("\x1b[0m")   # reset the color

    finally:
        # cleanup can be undefined when an exeption occurs during initialization
        if "cleanup" in locals():
            await cleanup()

        # the following only needed when testing the `errlog` key
        if "log_file_exit_stack" in locals():
            log_file_exit_stack.close()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
