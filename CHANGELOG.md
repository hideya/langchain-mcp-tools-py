# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).

## [Unreleased]

### Added
- **Streamable HTTP Transport Support**: Added support for the new Streamable HTTP transport (recommended for production)
- Transport identifier `"streamable_http"` to align with TypeScript version
- Deprecation warnings for legacy SSE transport
- Enhanced logging to show transport selection and deprecation notices
- Comprehensive documentation for Streamable HTTP migration
- Example code demonstrating different transport configurations

### Changed
- **BREAKING**: HTTP/HTTPS URLs now default to `streamable_http` transport instead of `sse`
- **BREAKING**: Transport identifier changed from `"streamable-http"` to `"streamable_http"` (underscore) for TypeScript alignment
- Prioritized Streamable HTTP over SSE in transport selection logic
- Enhanced error messages to reflect new transport priorities
- Updated documentation to emphasize Streamable HTTP as the recommended transport
- Added deprecation warnings for SSE transport usage

### Deprecated
- SSE transport is now deprecated in favor of Streamable HTTP
- Users will see warnings when using `transport: "sse"`

### Migration Guide
- Remove explicit `transport: "sse"` from configurations to use the new `streamable_http` default
- Update server endpoints to support Streamable HTTP transport
- Monitor logs for deprecation warnings and plan SSE phase-out
- See `docs/streamable-http-support.md` for detailed migration instructions

### Fixed
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
