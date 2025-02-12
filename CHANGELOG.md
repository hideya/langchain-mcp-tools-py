# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).

## [Unreleased]

### Added

### Changed

### Fixed

## [0.1.5] - 2025-02-12

### Added

### Changed

- Update example code in README.md to use `claude-3-5-sonnet-latest`
  instead of `haiku` which is sometimes less capable to handle results from MCP

### Fixed

- Better checks when converting MCP's results into `str`
- Content field of tool result is wrong [#8](https://github.com/hideya/langchain-mcp-tools-py/issues/8)
