# Ref: https://github.com/modelcontextprotocol/python-sdk/blob/main
#       /tests/shared/test_ws.py
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
from starlette.routing import WebSocketRoute

from mcp.server import Server
from mcp.server.websocket import websocket_server
from mcp.shared.exceptions import McpError
from mcp.types import (
    ErrorData,
    TextContent,
    Tool,
)

SERVER_NAME = "test_server_for_WS"


def get_available_port() -> int:
    """Find an available port dynamically."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def server_url(port: int) -> str:
    """Get the server URL for a given port."""
    return f"ws://127.0.0.1:{port}"


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
                    description="A test tool",
                    inputSchema={"type": "object", "properties": {}},
                )
            ]

        @self.call_tool()
        async def handle_call_tool(name: str, args: dict) -> list[TextContent]:
            return [TextContent(type="text", text=f"Called {name}")]


# Test fixtures
def make_server_app() -> Starlette:
    """Create test Starlette app with WebSocket transport"""
    server = ServerTest()

    async def handle_ws(websocket):
        try:
            async with websocket_server(
                websocket.scope, websocket.receive, websocket.send
            ) as streams:
                await server.run(
                    streams[0],
                    streams[1],
                    server.create_initialization_options()
                )
        except (asyncio.CancelledError, ConnectionError) as _:
            # Handle client disconnection gracefully
            print("WebSocket client disconnected")
        except Exception as e:
            # Log other unexpected errors
            print(f"Error in WebSocket handler: {e}")

    app = Starlette(
        routes=[
            WebSocketRoute("/ws", endpoint=handle_ws),
        ]
    )

    return app


async def run_server_async(port: int, shutdown_event: asyncio.Event = None):
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


# Class to manage the WebSocket server process
class WebSocketServerManager:
    def __init__(self):
        self.server_thread = None
        self.port = None
        self.shutdown_event = None
        self.running = False
        self.loop = None
        self.server_task = None

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
    parser = argparse.ArgumentParser(description="Run a WebSocket server")
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

    ws_url = server_url(port)
    print(f"Starting WebSocket server at {ws_url}")
    print(f"WebSocket endpoint available at {ws_url}/ws")
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
    """Example of how to use the WebSocketServerManager"""
    manager = WebSocketServerManager()
    try:
        port = manager.spawn_server()
        ws_url = server_url(port)
        
        print(f"Server started on port {port}")
        print(f"WebSocket server URL: {ws_url}")
        print(f"WebSocket endpoint: {ws_url}/ws")
        
        # Do something with the server...
        import time
        time.sleep(10)
        print("Example server running for 10 seconds completed")
    finally:
        # Ensure the server is terminated
        manager.terminate_server()
        print("Server terminated")


if __name__ == "__main__":
    main()
