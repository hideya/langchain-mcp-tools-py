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


# A very simple logger
def init_logger() -> logging.Logger:
    logging.basicConfig(
        # level=logging.DEBUG,
        level=logging.INFO,
        format="\x1b[90m%(levelname)s:\x1b[0m %(message)s"
    )
    return logging.getLogger()


async def run() -> None:
    load_dotenv()

    try:
        mcp_servers: McpServersConfig = {
            "filesystem": {
                # "transport": "stdio",  // optional
                # "type": "stdio",  // optional: VSCode-style config works too
                "command": "npx",
                "args": [
                    "-y",
                    "@modelcontextprotocol/server-filesystem",
                    "."  # path to a directory to allow access to
                ],
                # "cwd": "/tmp"  # the working dir to be use by the server
            },

            "fetch": {
                "command": "uvx",
                "args": [
                    "mcp-server-fetch"
                ]
            },
            
            # Example of authentication via Authorization header
            # https://github.com/github/github-mcp-server?tab=readme-ov-file#remote-github-mcp-server
            "github": {
                # To avoid auto protocol fallback, specify the protocol explicitly when using authentication
                "type": "http",
                # "__pre_validate_authentication": False,
                "url": "https://api.githubcopilot.com/mcp/",
                "headers": {
                    "Authorization": f"Bearer {os.environ.get('GITHUB_PERSONAL_ACCESS_TOKEN')}"
                }
            },
            
            # For MCP servers that require OAuth, consider using "mcp-remote"
            "notion": {
                "command": "npx",
                "args": ["-y", "mcp-remote", "https://mcp.notion.com/mcp"],
            },
        }
        
        queries = [
            "Read and briefly summarize the LICENSE file in the current directory",
            "Fetch the raw HTML content from bbc.com and tell me the titile",
            "Tell me about my GitHub profile",
            "Tell me about my Notion account",
        ]
        
        # If you are interested in MCP server's stderr redirection,
        # uncomment the following code snippets.
        #
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

        tools, cleanup = await convert_mcp_to_langchain_tools(
            mcp_servers,
            # logging.DEBUG
            # init_logger()
        )
        
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
        
        ### https://console.groq.com/docs/rate-limits
        ### https://console.groq.com/dashboard/usage
        # model_name = "groq:openai/gpt-oss-20b"

        ### https://cloud.cerebras.ai
        ### https://inference-docs.cerebras.ai/models/openai-oss
        ### FIXME: init_chat_model() doesn't support "cerebras"
        # from langchain_cerebras import ChatCerebras
        # model = ChatCerebras(model="gpt-oss-120b")

        model = init_chat_model(model_name)

        agent = create_agent(
            model,
            tools
        )
        
        print("\x1b[32m", end="")  # color to green
        print("\nLLM model:", getattr(model, 'model', getattr(model, 'model_name', 'unknown')))
        print("\x1b[0m", end="")  # reset the color
        
        for query in queries:
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

        # the followings only needed when testing the `url` key
        if "sse_server_process" in locals():
            sse_server_process.terminate()
        if "ws_server_process" in locals():
            ws_server_process.terminate()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
