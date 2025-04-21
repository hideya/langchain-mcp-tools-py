"""
Utility functions for starting and managing remote MCP servers for testing.
"""

import socket
import subprocess
import select
import time


# NOTE: Hard-coded dependency on the Supergateway message
# to easily identify the end of initialization.
SUPERGATEWAY_READY_MESSAGE = "[supergateway] Listening on port"


def find_free_port():
    """Find and return a free port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))  # Bind to a free port provided by the system
        return s.getsockname()[1]  # Return the port number assigned


def start_remote_mcp_server_locally(
        transport_type, mcp_server_run_command, timeout=30):
    """
    Start an MCP server process via supergateway with the specified transport
    type. Supergateway runs MCP stdio-based servers over SSE or WebSockets
    and is used here to run local SSE/WS servers for connection testing.
    Ref: https://github.com/supercorp-ai/supergateway

    Args:
        transport_type (str): The transport type, either 'sse' or 'ws'
        mcp_server_run_command (str): The command to run the MCP server
        timeout (int): Maximum time to wait for server startup in seconds

    Returns:
        tuple: (server_process, server_port)

    Raises:
        TimeoutError: If the server doesn't start within the timeout period
        ValueError: If the transport type is not supported
    """
    server_port = find_free_port()

    # Base command common to both server types
    command = [
        "npx",
        "-y",
        "supergateway",
        "--stdio",
        mcp_server_run_command,
        "--port", str(server_port),
    ]

    # Add transport-specific arguments
    if transport_type.lower() == 'sse':
        command.extend([
            "--baseUrl", f"http://localhost:{server_port}",
            "--ssePath", "/sse",
            "--messagePath", "/message"
        ])
    elif transport_type.lower() == 'ws':
        command.extend([
            "--outputTransport", "ws",
            "--messagePath", "/message"
        ])
    else:
        raise ValueError(f"Unsupported transport type: {transport_type}")

    # Start the server process with piped stdout/stderr
    print(f"Starting {transport_type.upper()} MCP Server Process...")
    server_process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1  # Line buffered
    )

    # Wait for the server to start by watching for the specific log message
    start_time = time.time()
    ready_message = SUPERGATEWAY_READY_MESSAGE
    poll_obj = select.poll()
    poll_obj.register(server_process.stdout, select.POLLIN)

    while True:
        # Check if process is still running
        if server_process.poll() is not None:
            # Process exited
            returncode = server_process.poll()
            error_output = server_process.stderr.read()
            raise RuntimeError(
                f"Server process exited with code {returncode} "
                f"before starting: {error_output}"
            )

        # Check for timeout
        if time.time() - start_time > timeout:
            server_process.terminate()
            raise TimeoutError(
                f"Timed out waiting for {transport_type.upper()} "
                f"server to start after {timeout} seconds"
            )

        # Check for output
        if poll_obj.poll(100):  # 100ms timeout
            line = server_process.stdout.readline().strip()
            print(line)  # Echo to console

            if ready_message in line:
                print(f"{transport_type.upper()} MCP Server is ready "
                      f"on port {server_port}")
                break

    # Start a thread to continue reading and printing output
    def _monitor_output(process):
        import threading

        def _reader(stream, is_error):
            # prefix = "ERROR: " if is_error else ""
            prefix = ""
            for line in stream:
                print(f"{prefix}{line.strip()}")

        threading.Thread(
            target=_reader,
            args=(process.stdout, False),
            daemon=True
        ).start()

        threading.Thread(
            target=_reader,
            args=(process.stderr, True),
            daemon=True
        ).start()

    # Start monitoring the output in the background
    _monitor_output(server_process)

    return server_process, server_port
