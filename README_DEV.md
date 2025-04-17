# Making Changes to langchain-mcp-tools

Thank you for your interest in langchain-mcp-tools!  
This guide is focused on the technical aspects of making changes to this project.

## Development Environment Setup

### Prerequisites

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) - A fast Python package installer and resolver
- `make` - The project uses Makefile to simplify the development workflow
- git

### Setting Up Your Environment

The following will create and activate a virtual environment using `uv`, if not already done,
and install the package using `uv pip install -e . `
including additional dependencies needed to develop and test.

   ```bash
   make install
   ```

## Project Architecture Overview

The project follows a simple and focused architecture:

- **Core functionality**: The main module `langchain_mcp_tools.py` contains the functionality to convert MCP server tools into LangChain tools.

- **Key components**:
  - `convert_mcp_to_langchain_tools`: The main entry point that handles parallel initialization of MCP servers and tool conversion
  - `spawn_mcp_server_and_get_transport`: Handles different types of MCP server initialization (stdio, SSE, WebSocket)
  - `get_mcp_server_tools`: Converts MCP tools to LangChain format using a custom adapter class

- **Data flow**: 
  1. MCP server configurations are provided
  2. Servers are initialized in parallel
  3. Available tools are retrieved from each server
  4. Tools are converted to LangChain format
  5. A cleanup function is returned to handle resource management

## Development Workflow

1. **Making changes**

   When making changes, keep the following in mind:
   - Maintain type hints for all functions and classes
   - Follow the existing code style (the project uses standard Python formatting)
   - Add comments for complex logic

2. **Test changes quickly**

   The project includes a simple usage example that can be used to test changes:

   ```bash
   make run-simple-usage
   ```

3. **Running tests**

   The tests are still in a preliminary stage, but it may help to identify possible bugs.  
   Please try the following to run the (very small) test suite with pytest.

   ```bash
   make test
   ```

4. **Clean build artifacts**

   Try clean-build once you feel comfortable with your changes.
 
   The following will remove all files that aren't git-controlled, except `.env'.  
   That means it will remove files you've created that aren't checked in,
   the virtual environment, and all cache files.

   ```bash
   make clean
   ```

5. **Building the package**

   The following will build the package and verify it's correctly structured.  
   Note that this will also perform `make clean` against the repository,
   i.e. remove all files other than those controlled by git and the `.env` file.

   ```bash
   make build
   ```

   This will:
   1. Clean previous build artifacts
   2. Install the package in development mode
   3. Build the distribution packages (wheel and tarball)
   4. Check the built packages with twine

---

If you have any questions about development that aren't covered here, please open an issue for discussion.
