# Streamable HTTP Transport Support

This document describes the Streamable HTTP transport support in langchain-mcp-tools.

## Overview

The Streamable HTTP transport is the **recommended MCP transport** that supersedes SSE (Server-Sent Events) for production deployments. It provides better scalability, resumability, and performance for multi-node deployments.

**Key Points:**
- **Default Transport**: Streamable HTTP is now the default for HTTP/HTTPS URLs
- **Alignment**: Uses `"streamable_http"` identifier to align with TypeScript version
- **Deprecation**: SSE transport is deprecated and will show warnings

## Key Changes Made

### 1. Enhanced URL-based Configuration

The `McpServerUrlBasedConfig` now supports an explicit `transport` field with Streamable HTTP as the default:

```python
class McpServerUrlBasedConfig(TypedDict):
    url: str
    transport: NotRequired[str]  # "streamable_http", "sse", "websocket"
    headers: NotRequired[dict[str, str] | None]
    timeout: NotRequired[float]
    # ... other fields
```

### 2. Updated Transport Selection Logic

The `spawn_mcp_server_and_get_transport()` function now:

- **Prioritizes Streamable HTTP**: Default transport for HTTP/HTTPS URLs
- **Explicit transport selection**: Uses the `transport` field when specified
- **Deprecation warnings**: Shows warnings when using legacy SSE transport
- **Better error handling**: Provides clear error messages for unsupported transports

### 3. Transport Priority (Updated)

1. **Streamable HTTP (Default)**: Default for `http://`/`https://` URLs
2. **Explicit transport**: If `transport` field is specified, use that transport
3. **Legacy SSE**: Only when explicitly specified with `transport: "sse"`
4. **WebSocket**: For `ws://`/`wss://` URLs or explicit `transport: "websocket"`

## Configuration Examples

### Streamable HTTP Server (Recommended, Default for HTTP)

```python
server_configs = {
    "production-api": {
        "url": "https://api.example.com/mcp",
        "transport": "streamable_http",  # Optional: this is now the default
        "headers": {"Authorization": "Bearer token123"},
        "timeout": 60.0
    }
}

# Or simply (streamable_http is now the default):
server_configs = {
    "production-api": {
        "url": "https://api.example.com/mcp",
        "headers": {"Authorization": "Bearer token123"},
        "timeout": 60.0
    }
}
```

### Legacy SSE Server (Deprecated)

```python
server_configs = {
    "legacy-api": {
        "url": "https://api.example.com/mcp/sse",
        "transport": "sse",  # Must be explicit now
        "headers": {"Authorization": "Bearer token123"}
    }
}
```

### Mixed Configuration

```python
server_configs = {
    "local-filesystem": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "."]
    },
    "remote-streamable": {
        "url": "https://api.example.com/mcp",
        # transport defaults to "streamable_http" for http/https URLs
        "headers": {"Authorization": "Bearer token123"},
        "timeout": 60.0
    },
    "legacy-sse": {
        "url": "https://legacy.example.com/mcp/sse",
        "transport": "sse",  # Explicit for legacy servers
    },
    "websocket-server": {
        "url": "wss://ws.example.com/mcp",
        "transport": "websocket"
    }
}
```

## Migration Guide

### From SSE to Streamable HTTP

1. **Remove explicit SSE transport** (if you want to use the new default):
   ```python
   # Old SSE configuration (explicit)
   config = {
       "url": "https://api.example.com/mcp/sse",
       "transport": "sse",
       "headers": {"Authorization": "Bearer token"}
   }
   
   # New Streamable HTTP configuration (default)
   config = {
       "url": "https://api.example.com/mcp",
       # No need to specify transport - streamable_http is default
       "headers": {"Authorization": "Bearer token"},
       "timeout": 60.0  # Optional: customize timeout
   }
   ```

2. **Update server endpoints**: Ensure your server supports Streamable HTTP on the specified URL

3. **Test the connection**: The library will log which transport is being used and show deprecation warnings for SSE

### Alignment with TypeScript Version

This Python implementation now aligns with the TypeScript version:
- Uses `"streamable_http"` instead of `"streamable-http"`
- Prioritizes Streamable HTTP as the default for HTTP/HTTPS URLs
- Maintains the same configuration patterns and behavior

## Benefits of Streamable HTTP

1. **Better Scalability**: Designed for multi-node deployments
2. **Resumability**: Supports event stores for resumable connections
3. **Performance**: More efficient than SSE for high-throughput scenarios
4. **Flexibility**: Supports both JSON and SSE response formats
5. **Future-Proof**: This is the recommended transport going forward

## Backward Compatibility

- Existing SSE configurations continue to work when explicitly specified
- Deprecation warnings will be shown for SSE usage to encourage migration
- WebSocket transport remains unchanged
- Local stdio servers (command-based) are unaffected

## Error Handling

The updated code provides better error messages for unsupported transports:

```python
ValueError: Unsupported transport "invalid-transport" or URL scheme "http" for server "my-server". 
Supported transports: "streamable_http" (recommended), "sse" (deprecated), "websocket". 
Supported URL schemes: http/https (for streamable_http/sse), ws/wss (for websocket).
```

## Logging

The enhanced logging shows which transport is being used and deprecation warnings:

```
[INFO] MCP server "my-server": connecting via Streamable HTTP to https://api.example.com/mcp
[INFO] MCP server "legacy-server": connecting via SSE (legacy) to https://legacy.example.com/mcp/sse
[WARNING] MCP server "legacy-server": SSE transport is deprecated, consider migrating to streamable_http
[INFO] MCP server "ws-server": connecting via WebSocket to wss://ws.example.com/mcp
[INFO] MCP server "local-server": spawning local process via stdio
```

## Testing

To test the Streamable HTTP support:

1. **Set up a test server** that supports Streamable HTTP
2. **Configure the client** with or without `transport: "streamable_http"` (it's now the default)
3. **Check the logs** to confirm the correct transport is being used
4. **Verify tool functionality** works as expected
5. **Test deprecation warnings** by explicitly using `transport: "sse"`

## Future Considerations

- Monitor MCP specification updates for new transport features
- Consider adding authentication support for Streamable HTTP
- Evaluate performance improvements over SSE in your use case
- Plan migration timeline from SSE to Streamable HTTP for production systems
- Keep alignment with TypeScript version for consistent behavior across implementations

## Transport Comparison

| Transport | Status | Use Case | Performance | Scalability |
|-----------|--------|----------|-------------|-------------|
| `streamable_http` | **Recommended** | Production deployments | High | Excellent |
| `sse` | Deprecated | Legacy systems only | Medium | Limited |
| `websocket` | Supported | Real-time applications | High | Good |
| `stdio` | Supported | Local development | High | N/A |

## Breaking Changes

### Version 2.0+ Changes

1. **Default Transport Change**: HTTP/HTTPS URLs now default to `streamable_http` instead of `sse`
2. **Transport Identifier**: Uses `"streamable_http"` (with underscore) to align with TypeScript version
3. **Deprecation Warnings**: SSE usage now shows deprecation warnings
4. **Error Messages**: Updated to reflect new transport priorities

### Migration Checklist

- [ ] Update server endpoints to support Streamable HTTP
- [ ] Test existing configurations with new defaults
- [ ] Address any deprecation warnings in logs
- [ ] Update documentation and configuration examples
- [ ] Plan phaseout of SSE transport usage

## Troubleshooting

### Common Issues

1. **Server doesn't support Streamable HTTP**:
   - Explicitly set `transport: "sse"` for legacy servers
   - Check server documentation for supported transports

2. **Connection failures**:
   - Verify the server URL and endpoint
   - Check authentication headers and tokens
   - Review server logs for errors

3. **Performance issues**:
   - Adjust `timeout` settings for slow connections
   - Monitor network latency and server response times

4. **Deprecation warnings**:
   - Plan migration from SSE to Streamable HTTP
   - Update server infrastructure to support Streamable HTTP
