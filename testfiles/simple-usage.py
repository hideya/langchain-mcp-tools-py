# Standard library imports
import asyncio
import logging
import sys
from contextlib import ExitStack
from typing import (
    Any,
    Dict,
)

# Third-party imports
try:
    from dotenv import load_dotenv
    from langchain.chat_models import init_chat_model
    from langchain.schema import HumanMessage
    from langgraph.prebuilt import create_react_agent
except ImportError as e:
    print(f'\nError: Required package not found: {e}')
    print('Please ensure all required packages are installed\n')
    sys.exit(1)

# Local application imports
from langchain_mcp_tools import convert_mcp_to_langchain_tools


# A very simple logger
def init_logger() -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,  # logging.DEBUG,
        format='\x1b[90m%(levelname)s:\x1b[0m %(message)s'
    )
    return logging.getLogger()


async def run() -> None:
    load_dotenv()

    try:
        mcp_servers: Dict[str, Dict[str, Any]] = {
            'filesystem': {
                'command': 'npx',
                'args': [
                    '-y',
                    '@modelcontextprotocol/server-filesystem',
                    '.'  # path to a directory to allow access to
                ],
                'cwd': '/tmp'  # the working directory to be use by the server
            },
            'fetch': {
                'command': 'uvx',
                'args': [
                    'mcp-server-fetch'
                ]
            },
            'weather': {
                'command': 'npx',
                'args': [
                    '-y',
                    '@h1deya/mcp-server-weather'
                ]
            },
        }

        # Set the file descriptors to which MCP server's stderr is redirected
        # NOTE: Why the key name `stderr` was chosen:
        # Unlike the TypeScript SDK's `StdioServerParameters`, the Python SDK's
        # `StdioServerParameters` doesn't include `stderr`.
        # Instead, it calls `stdio_client()` with a separate argument
        # `errlog`.  I once thought of using `errlog` for the key for the
        # Pyhton version, but decided to follow the TypeScript version since
        # its public API already exposes the key name and I choose consistency.
        log_file_exit_stack = ExitStack()
        for server_name in mcp_servers:
            log_path = f'mcp-server-{server_name}.log'
            log_file = open(log_path, 'w')
            mcp_servers[server_name]['stderr'] = log_file.fileno()
            log_file_exit_stack.callback(log_file.close)

        tools, cleanup = await convert_mcp_to_langchain_tools(
            mcp_servers,
            # init_logger()
        )

        llm = init_chat_model(
            # model='claude-3-7-sonnet-latest',
            # model_provider='anthropic'
            model='o3-mini',
            model_provider='openai'
        )

        agent = create_react_agent(
            llm,
            tools
        )

        # query = 'Read the news headlines on bbc.com'
        # query = 'Read and briefly summarize the LICENSE file'
        query = 'Tell me the number of directories in the current directory';
        # query = "Tomorrow's weather in SF?"

        print('\x1b[33m')  # color to yellow
        print(query)
        print('\x1b[0m')   # reset the color

        messages = [HumanMessage(content=query)]

        result = await agent.ainvoke({'messages': messages})

        result_messages = result['messages']
        # the last message should be an AIMessage
        response = result_messages[-1].content

        print('\x1b[36m')  # color to cyan
        print(response)
        print('\x1b[0m')   # reset the color

    finally:
        if cleanup is not None:
            await cleanup()
        log_file_exit_stack.close()


def main() -> None:
    asyncio.run(run())


if __name__ == '__main__':
    main()
