# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).

## [Unreleased]

### Changed
- Minor README.md refinements

## [0.2.10] - 2025-07-06

### Fixed
- Properly export McpInitializationError


## [0.2.9] - 2025-07-05

### Changed
- Update logger argument to take logging level (e.g. logging.DEBUG) as well
- Separate out the tool conversion function into tool_adapter.py
- Separate out the transport utility functions into ransport_utils.py
- Update README.md
- Update dependencies


## [0.2.8] - 2025-06-29

### Changed
- Update documentation
- Use leading underscores for the internal functions


## [0.2.7] - 2025-06-28

### Changed
- Improve log messages for authentication pre-validation
- Minor updates to README.md


## [0.2.6] - 2025-06-27

### Changed
- Update dependencies


## [0.2.5] - 2025-06-27

### Added
- Streamable HTTP Support with MCP 2025-03-26 backwards compatibility guidelines
- Test servers and clients for Streamable HTTP
- Support for Google GenAI LLMs
- McpInitializationError for configuration and connection errors
- TECHNOCAL.md that explains the implemenation details

### Changed
- Update all documentation to include Streamable HTTP Support
- Improve logging to show detailed transport selection reasoning
- Rename testfiles/sse-auth-test-{client,server}.py to use "_" instead of "-" 
- Update dependencies


## [0.2.4] - 2025-04-24

### Changed
- Make SingleMcpServerConfig public (it used to be McpServerConfig)
- Improve documentation
- Update README.md


## [0.2.3] - 2025-04-22

### Added
- Add test files for SSE connection with authentication
- Add Sphinx documentation with Google-style docstrings


## [0.2.2] - 2025-04-17

### Changed
- Add new key "headers" to url based config for SSE server
- Update README.md for the newly introduced headers key
- Add README_DEV.md
- Use double quotes instead of single quotes for string literals
- Update dependencies


## [0.2.1] - 2025-04-11

### Changed
- Update dependencies
- Minor updates to the README.md


## [0.2.0] - 2025-04-04

### Changed
- Add support for SSE and Websocket remote MCP servers
- Introduced `McpServersConfig` type
- Changed `stderr` of `McpServersConfig` to `errlog` to follow Python SDK more closely
- Use double quotes instead of single quotes for string literals


## [0.1.11] - 2025-03-31

### Changed
- Update the dependencies, esp. `Updated mcp v1.2.0 -> v1.6.0` (this fixes Issue #22)
- Add `cwd` to `server_config` to specify the working directory for the MCP server to use
- Add `stderr` to specify a filedescriptor to which MCP server's stderr is redirected
- Rename `examples/example.py` to `testfiles/simple-usage.py` to avoid confusion


## [0.1.10] - 2025-03-25

### Changed
- Make the logger fallback to a pre-configured logger if no root handlers exist
- Remove unnecessarily added python-dotenv from the dependencies
- Minor updates to README.me


## [0.1.9] - 2025-03-19

### Changed
- Update LLM models used in example.py


## [0.1.8] - 2025-03-13

### Fixed
- [PR #14](https://github.com/hideya/langchain-mcp-tools-py/pull/14): Fix: Handle JSON Schema type: ["string", "null"] for Notion MCP tools

### Changed
- Minor updates to README.me and example.py


## [0.1.7] - 2025-02-21

### Fixed
- [Issue #11](https://github.com/hideya/langchain-mcp-tools-py/issues/11): Move some dev dependencies which are mistakenly in dependencies to the right section


## [0.1.6] - 2025-02-20

### Added
- `make test-publish` target to handle publication more carefully

### Changed
- Estimate the size of returning text in a simpler way
- Return a text with reasonable explanation when no text return found


## [0.1.5] - 2025-02-12

### Fixed
- [Issue #8](https://github.com/hideya/langchain-mcp-tools-py/issues/8): Content field of tool result is wrong
- Better checks when converting MCP's results into `str`

### Changed
- Update example code in README.md to use `claude-3-5-sonnet-latest`
  instead of `haiku` which is sometimes less capable to handle results from MCP
