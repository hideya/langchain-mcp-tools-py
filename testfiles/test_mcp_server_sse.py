# Ref: https://github.com/modelcontextprotocol/python-sdk/blob/main
#       /tests/shared/test_sse.py
import argparse
import asyncio
import signal
import socket
import threading
from typing import Optional

import anyio
import uvicorn
from pydantic import AnyUrl
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Mount, Route

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.shared.exceptions import McpError
from mcp.types import (
    ErrorData,
    TextContent,
    Tool,
)

SERVER_NAME = "test_server_for_SSE"


def get_available_port() -> int:
    """Find an available port dynamically."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def server_url(port: int) -> str:
    """Get the server URL for a given port."""
    return f"http://127.0.0.1:{port}"


# Test server implementation
class ServerTest(Server):
    def __init__(self):
        super().__init__(SERVER_NAME)

        @self.read_resource()
        async def handle_read_resource(uri: AnyUrl) -> str | bytes:
            if uri.scheme == "foobar":
                return f"Read {uri.host}"
            elif uri.scheme == "slow":
                # Simulate a slow resource
                await anyio.sleep(2.0)
                return f"Slow response from {uri.host}"

            raise McpError(
                error=ErrorData(
                    code=404, message="No resource with that URI was found"
                )
            )

        @self.list_tools()
        async def handle_list_tools() -> list[Tool]:
            return [
                Tool(
                    name="test_tool",
                    description="A SSE test tool",
                    inputSchema={"type": "object", "properties": {}},
                )
            ]

        @self.call_tool()
        async def handle_call_tool(name: str, args: dict) -> list[TextContent]:
            return [TextContent(type="text", text=f"Called {name}")]


# Server app creation
def make_server_app() -> Starlette:
    """Create test Starlette app with SSE transport"""
    sse = SseServerTransport("/messages/")
    server = ServerTest()

    async def handle_sse(request: Request):
        """Handle SSE connections with better error handling for
        client disconnection."""
        from starlette.responses import Response

        try:
            async with sse.connect_sse(
                request.scope, request.receive, request._send
            ) as streams:
                await server.run(
                    streams[0],
                    streams[1],
                    server.create_initialization_options()
                )
            return Response(status_code=200)
        except (asyncio.CancelledError, ConnectionError) as _:
            # Handle client disconnection gracefully
            print("SSE Client disconnected")
            return Response(status_code=204)  # No content - connection closed
        except Exception as e:
            # Log other unexpected errors
            print(f"Error in SSE handler: {e}")
            # Internal server error
            return Response(status_code=500, content=str(e))

    app = Starlette(
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ]
    )

    return app


async def run_server_async(port: int, shutdown_event: asyncio.Event):
    """Run the server asynchronously with graceful shutdown."""
    app = make_server_app()
    config = uvicorn.Config(
        app=app, 
        host="127.0.0.1",
        port=port, 
        log_level="error",
        lifespan="off"  # Disable lifespan to avoid cancellation errors
    )
    server = uvicorn.Server(config)

    # Create shutdown event if not provided
    if shutdown_event is None:
        shutdown_event = asyncio.Event()

    # Only set up signal handlers in the main thread
    if threading.current_thread() is threading.main_thread():
        def signal_handler():
            shutdown_event.set()

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, signal_handler)

    # Start server task
    server_task = asyncio.create_task(server.serve())

    # Wait for shutdown signal
    await shutdown_event.wait()
    server.should_exit = True
    await server_task


# New class to manage the server process
class SseServerManager:
    def __init__(self):
        self.server_thread = None
        self.port = None
        self.shutdown_event = None
        self.running = False

    def spawn_server(self, port: Optional[int] = None) -> int:
        """
        Spawn a server in a separate thread with an available port and return
        the port number.

        Args:
            port: Optional port number to use. If None, an available port will
            be selected.

        Returns:
            int: The port number the server is running on

        Raises:
            RuntimeError: If server is already running or cannot be started
        """
        if self.running:
            raise RuntimeError("Server is already running")

        # Use provided port or get an available one
        self.port = port if port is not None else get_available_port()

        # Create a threading Event for checking server startup status
        server_started = threading.Event()
        server_error = [None]  # List to store error if one occurs

        # Create an asyncio event for shutdown signaling
        self.shutdown_event = asyncio.Event()

        # Define the thread target function
        def run_server_thread():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                # Store the loop for later shutdown
                self.loop = loop

                # Create a task to run the server and store it
                self.server_task = loop.create_task(
                    run_server_async(self.port, self.shutdown_event))

                # Signal that we've reached this point without errors
                server_started.set()

                # Run the event loop
                loop.run_forever()
            except Exception as e:
                server_error[0] = str(e)
                server_started.set()  # Signal even on error so we don't hang
            finally:
                # Clean up any pending tasks
                tasks = asyncio.all_tasks(loop)
                for task in tasks:
                    task.cancel()

                # Allow tasks to properly cancel
                if tasks:
                    loop.run_until_complete(
                        asyncio.gather(*tasks, return_exceptions=True))

                loop.close()
                self.running = False

        # Start the server in a new thread
        self.server_thread = threading.Thread(
            target=run_server_thread, daemon=True)
        self.server_thread.start()
        self.running = True

        # Wait for the server to start (with timeout)
        if not server_started.wait(timeout=5.0):
            self.running = False
            raise RuntimeError("Server startup timed out")

        # Check if an error occurred during startup
        if server_error[0]:
            self.running = False
            raise RuntimeError(f"Failed to start server: {server_error[0]}")

        return self.port

    def terminate_server(self) -> bool:
        """
        Terminate the running server.

        Returns:
            bool: True if server was terminated, False if it wasn't running
        """
        if (not self.running or
                not self.server_thread or
                not self.server_thread.is_alive()):
            return False

        if hasattr(self, 'loop') and self.loop.is_running():
            try:
                # Signal the shutdown event
                if hasattr(self, 'shutdown_event') and self.shutdown_event:
                    self.loop.call_soon_threadsafe(self.shutdown_event.set)

                # Give some time for graceful shutdown
                import time
                time.sleep(0.5)

                # Stop the event loop
                self.loop.call_soon_threadsafe(self.loop.stop)
            except RuntimeError:
                # The loop might already be closed
                pass

        # Wait for the thread to terminate (with timeout)
        self.server_thread.join(timeout=5.0)

        # If thread didn't terminate, log it but continue cleanup
        if self.server_thread.is_alive():
            print("Warning: Server thread did not terminate cleanly")

        # Reset state
        self.running = False
        self.shutdown_event = None
        self.server_thread = None

        # Clean up references
        if hasattr(self, 'server_task'):
            delattr(self, 'server_task')
        if hasattr(self, 'loop'):
            delattr(self, 'loop')

        return True


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run an SSE server")
    parser.add_argument(
        "--port",
        "-p",
        type=int,
        help="Port for the server (default: auto-select an available port)"
    )
    return parser.parse_args()


def main():
    """Main entry point for the server."""
    args = parse_args()

    # Use provided port or get an available one
    port = args.port if args.port is not None else get_available_port()

    sse_url = server_url(port)
    print(f"Starting SSE server at {sse_url}")
    print(f"SSE endpoint available at {sse_url}/sse")
    print(f"Messages endpoint available at {sse_url}/messages/")
    print("Press Ctrl+C to stop the server")

    try:
        asyncio.run(run_server_async(port))
    except KeyboardInterrupt:
        print("\nServer stopped")
    except Exception as e:
        print(f"\nError starting server: {e}")
        # If port is already in use or other similar errors
        if args.port is not None:
            print("Try using a different port or omitting the port argument "
                  "to auto-select one")


# Example usage of the server manager
def example_usage():
    """Example of how to use the SseServerManager"""
    manager = SseServerManager()
    try:
        port = manager.spawn_server()
        print(f"Server started on port {port}")

        # Do something with the server...
        import time
        time.sleep(10)
    finally:
        # Ensure the server is terminated
        manager.terminate_server()
        print("Server terminated")


if __name__ == "__main__":
    main()
    # Uncomment to run the example:
    # example_usage()
