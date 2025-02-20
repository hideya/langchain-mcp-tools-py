# Standard library imports
import asyncio
import logging
import os
import sys

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
        format='\x1b[90m[%(levelname)s]\x1b[0m %(message)s'
    )
    return logging.getLogger()


async def run() -> None:
    load_dotenv()
    if not os.environ.get('ANTHROPIC_API_KEY'):
        raise Exception('ANTHROPIC_API_KEY env var needs to be set')
    # if not os.environ.get('OPENAI_API_KEY'):
    #     raise Exception('OPENAI_API_KEY env var needs to be set')

    try:
        mcp_configs = {
            'filesystem': {
                'command': 'npx',
                'args': [
                    '-y',
                    '@modelcontextprotocol/server-filesystem',
                    '.'  # path to a directory to allow access to
                ]
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

        tools, cleanup = await convert_mcp_to_langchain_tools(
            mcp_configs,
            init_logger()
        )

        llm = init_chat_model(
            model='claude-3-5-sonnet-latest',
            model_provider='anthropic',
            # model='gpt-4o',
            # model_provider='openai',
            temperature=0,
            max_tokens=1000
        )

        agent = create_react_agent(
            llm,
            tools
        )

        # query = 'Read the news headlines on bbc.com'
        # query = 'Read and briefly summarize the LICENSE file'
        query = "Tomorrow's weather in SF?"

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


def main() -> None:
    asyncio.run(run())


if __name__ == '__main__':
    main()
