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

    # If you are interested in testing the SSE/WS server connection, uncomment
    # one of the following code snippets and one of the appropriate "weather"
    # server configurations, while commenting out the others.

    # sse_server_process, sse_server_port = start_remote_mcp_server_locally(
    #     "SSE", "npx -y @h1deya/mcp-server-weather")

    # ws_server_process, ws_server_port = start_remote_mcp_server_locally(
    #     "WS", "npx -y @h1deya/mcp-server-weather")

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

            "us-weather": {  # US weather only
                "command": "npx",
                "args": [
                    "-y",
                    "@h1deya/mcp-server-weather"
                ]
            },

            # # Auto-detection example: This will try Streamable HTTP first, then fallback to SSE
            # "us-weather": {
            #     "url": f"http://localhost:{sse_server_port}/sse"
            # },
            
            # # THIS DOESN'T WORK: Example of explicit transport selection:
            # "us-weather": {
            #     "url": f"http://localhost:{streamable_http_server_port}/mcp",
            #     "transport": "streamable_http"  # Force Streamable HTTP
            #     # "type": "http"  # VSCode-style config also works instead of the above
            # },
            
            # "us-weather": {
            #     "url": f"http://localhost:{sse_server_port}/sse",
            #     "transport": "sse"  # Force SSE
            #     # "type": "sse"  # This also works instead of the above
            # },

            # "us-weather": {
            #     "url": f"ws://localhost:{ws_server_port}/message",
            #     # optionally `"transport": "ws"` or `"type": "ws"`
            # },
            
            # # https://github.com/modelcontextprotocol/servers/tree/main/src/brave-search
            # "brave-search": {
            #     "command": "npx",
            #     "args": [ "-y", "@modelcontextprotocol/server-brave-search"],
            #     "env": { "BRAVE_API_KEY": os.environ.get('BRAVE_API_KEY') }
            # },
            
            # # Example of authentication via Authorization header
            # # https://github.com/github/github-mcp-server?tab=readme-ov-file#remote-github-mcp-server
            # "github": {
            #     # To avoid auto protocol fallback, specify the protocol explicitly when using authentication
            #     "type": "http",
            #     # "__pre_validate_authentication": False,
            #     "url": "https://api.githubcopilot.com/mcp/",
            #     "headers": {
            #         "Authorization": f"Bearer {os.environ.get('GITHUB_PERSONAL_ACCESS_TOKEN')}"
            #     }
            # },
            
            # # NOTE: comment out "fetch" when you use "notion".
            # # They both have a tool named "fetch," which causes a conflict.
            # #
            # # Run Notion remote MCP server via mcp-remote
            # "notion": {
            #     "command": "npx",  # OAuth via "mcp-remote"
            #     "args": ["-y", "mcp-remote", "https://mcp.notion.com/mcp"],
            # },
                        
            # # The following Notion local MCP server is not recommended anymore?
            # # Refs:
            # # - https://developers.notion.com/docs/get-started-with-mcp
            # # - https://www.npmjs.com/package/@notionhq/notion-mcp-server
            # "notion": {
            #     "command": "npx",
            #     "args": ["-y", "@notionhq/notion-mcp-server"],
            #     "env": {
            #         "NOTION_TOKEN": os.environ.get("NOTION_INTEGRATION_SECRET", "")
            #     }
            # },
            
            # "airtable": {
            #     "transport": "stdio",
            #     "command": "npx",
            #     "args": ["-y", "airtable-mcp-server"],
            #     "env": {
            #         "AIRTABLE_API_KEY": f"{os.environ.get('AIRTABLE_API_KEY')}"
            #     }
            # },
            
            # "sqlite": {
            #     "command": "uvx",
            #     "args": [
            #         "mcp-server-sqlite",
            #         "--db-path",
            #         "mcp-server-sqlite-test.sqlite3"
            #     ],
            #     "cwd": "/tmp"  # the working directory to be use by the server
            # },

            # "sequential-thinking": {
            #     "command": "npx",
            #     "args": [
            #         "-y",
            #         "@modelcontextprotocol/server-sequential-thinking"
            #     ]
            # },

            # "playwright": {
            #     "command": "npx",
            #     "args": [
            #         "@playwright/mcp@latest"
            #     ]
            # },
        }

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

        ### https://docs.anthropic.com/en/docs/about-claude/pricing
        ### https://console.anthropic.com/settings/billing
        # llm = init_chat_model("anthropic:claude-3-5-haiku-latest")
        # llm = init_chat_model("anthropic:claude-sonnet-4-0")
        
        ### https://platform.openai.com/docs/pricing
        ### https://platform.openai.com/settings/organization/billing/overview
        # llm = init_chat_model("openai:gpt-4.1-nano")
        # llm = init_chat_model("openai:gpt-5-mini")
        
        ### https://ai.google.dev/gemini-api/docs/pricing
        ### https://console.cloud.google.com/billing
        llm = init_chat_model("google_genai:gemini-2.5-flash")
        # llm = init_chat_model("google_genai:gemini-2.5-pro")

        ### https://console.x.ai
        # llm = init_chat_model("xai:grok-3-mini")
        # llm = init_chat_model("xai:grok-4")
        
        ### https://console.groq.com/docs/rate-limits
        ### https://console.groq.com/dashboard/usage
        # llm = init_chat_model("groq:openai/gpt-oss-20b")
        # llm = init_chat_model("groq:openai/gpt-oss-120b")

        ### https://cloud.cerebras.ai
        ### https://inference-docs.cerebras.ai/models/openai-oss
        ### No init_chat_model() support for "cerebras" yet
        # from langchain_cerebras import ChatCerebras
        # llm = ChatCerebras(model="gpt-oss-120b")

        agent = create_react_agent(
            llm,
            tools
        )
        
        print("\x1b[32m");  # color to green
        print("\nLLM model:", getattr(llm, 'model', getattr(llm, 'model_name', 'unknown')))
        print("\x1b[0m");  # reset the color

        query = "Are there any weather alerts in California?"
        # query = "Read the news headlines on bbc.com"
        # query = "Read and briefly summarize the LICENSE file"
        # query = "Tell me how many directories there are in `.`"
        # query = "Tell me about my GitHub profile"
        # query = ("Make a new table in DB and put items apple and orange with counts 123 and 345 respectively, "
        #         "then increment the coutns by 1, and show all the items in the table.")
        # query = "Use sequential-thinking and plan a trip from Tokyo to San Francisco"
        # query = "Open the BBC.com page, then close it"
        # query = "Tell me about my Notion account"
        # query = "What's the news from Tokyo today?"
        
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
