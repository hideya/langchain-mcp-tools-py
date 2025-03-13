# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).

## [Unreleased]

### Added

### Changed

### Fixed

## [0.1.8] - 2025-03-13

### Added

### Changed

### Fixed

- [PR #14](https://github.com/hideya/langchain-mcp-tools-py/pull/14): Fix: Handle JSON Schema type: ["string", "null"] for Notion MCP tools


## [0.1.7] - 2025-02-21

### Added

### Changed

### Fixed

- [Issue #11](https://github.com/hideya/langchain-mcp-tools-py/issues/11): Move some dev dependencies which are mistakenly in dependencies to the right section


## [0.1.6] - 2025-02-20

### Added

- `make test-publish` target to handle publication more carefully

### Changed

- Estimate the size of returning text in more simpler way
- Return a text with reasonable explanation when no text return found

### Fixed


## [0.1.5] - 2025-02-12

### Added

### Changed

- Update example code in README.md to use `claude-3-5-sonnet-latest`
  instead of `haiku` which is sometimes less capable to handle results from MCP

### Fixed

- [Issue #8](https://github.com/hideya/langchain-mcp-tools-py/issues/8): Content field of tool result is wrong
- Better checks when converting MCP's results into `str`
