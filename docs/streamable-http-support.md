# Streamable HTTP Transport Support with MCP Spec Compliance

This document describes the Streamable HTTP transport support in langchain-mcp-tools, implementing the MCP specification's backwards compatibility recommendations.

## Overview

The Streamable HTTP transport is the **recommended MCP transport** that supersedes SSE (Server-Sent Events). Per the **MCP 2025-03-26 specification**, clients should attempt Streamable HTTP first, then fallback to SSE on 4xx errors for maximum compatibility.

**Key Points:**
- **Auto-Detection**: HTTP URLs automatically try Streamable HTTP first, fallback to SSE on 4xx errors
- **MCP Spec Compliance**: Implements the official backwards compatibility guidelines
- **Alignment**: Uses `"streamable_http"` identifier to align with TypeScript version
- **Deprecation**: SSE transport shows warnings to encourage migration

## MCP Specification Implementation

This implementation follows the [MCP 2025-03-26 specification](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports#backwards-compatibility) exactly:

### Backwards Compatibility Logic

```
Clients wanting to support older servers should:
- Accept an MCP server URL from the user, which may point to either a server using the old transport or the new transport.
- Attempt to POST an InitializeRequest to the server URL, with an Accept header as defined above:
  - If it succeeds, the client can assume this is a server supporting the new Streamable HTTP transport.
  - If it fails with an HTTP 4xx status code (e.g., 405 Method Not Allowed or 404 Not Found):
    - Issue a GET request to the server URL, expecting that this will open an SSE stream and return an endpoint event as the first event.
```

### Implementation Details

1. **Auto-Detection (Default)**: For HTTP/HTTPS URLs without explicit transport
   - Try Streamable HTTP connection first
   - On 4xx errors → fallback to SSE
   - Non-4xx errors → re-thrown (network issues, etc.)

2. **Explicit Transport**: When `transport` is specified
   - `"streamable_http"` → use Streamable HTTP only
   - `"sse"` → use SSE only (shows deprecation warning)
   - `"websocket"` → use WebSocket

3. **Error Classification**: 4xx errors include:
   - 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found
   - 405 Method Not Allowed, and other 4xx status codes

## Configuration Examples

### Auto-Detection (Recommended, MCP Spec Compliant)

```python
server_configs = {
    "modern-api": {
        "url": "https://api.example.com/mcp",
        # No transport specified - auto-detects per MCP spec:
        # 1. Try Streamable HTTP first
        # 2. Fallback to SSE on 4xx errors
        "headers": {"Authorization": "Bearer token123"},
        "timeout": 60.0
    }
}
```

### Explicit Streamable HTTP (No Fallback)

```python
server_configs = {
    "streamable-only": {
        "url": "https://api.example.com/mcp",
        "transport": "streamable_http",  # Explicit, no fallback
        "headers": {"Authorization": "Bearer token123"},
        "timeout": 60.0
    }
}
```

### Explicit SSE (Legacy, Deprecated)

```python
server_configs = {
    "legacy-api": {
        "url": "https://api.example.com/mcp/sse",
        "transport": "sse",  # Explicit, shows deprecation warning
        "headers": {"Authorization": "Bearer token123"}
    }
}
```

### Mixed Configuration (Real-World Scenario)

```python
server_configs = {
    "local-filesystem": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "."]
    },
    "modern-api": {
        "url": "https://api.example.com/mcp",
        # Auto-detection: tries Streamable HTTP → SSE fallback
        "headers": {"Authorization": "Bearer token123"}
    },
    "legacy-partner": {
        "url": "https://partner.example.com/mcp/sse",
        "transport": "sse",  # Explicit for known legacy server
        "headers": {"Authorization": "Bearer partner_token"}
    },
    "websocket-server": {
        "url": "wss://realtime.example.com/mcp",
        "transport": "websocket"
    }
}
```

## Benefits of This Implementation

### 1. **Maximum Compatibility**
- Works with modern Streamable HTTP servers
- Automatically falls back to legacy SSE servers
- No configuration changes needed for most users

### 2. **MCP Spec Compliance**
- Follows official MCP 2025-03-26 backwards compatibility guidelines
- Aligns with reference implementations
- Future-proof as the standard evolves

### 3. **Graceful Migration Path**
- Existing SSE servers continue to work via auto-fallback
- New servers get Streamable HTTP benefits automatically
- Clear deprecation warnings guide migration

### 4. **TypeScript Alignment**
- Same behavior as TypeScript langchain-mcp-tools
- Consistent `"streamable_http"` identifier
- Matching error handling and fallback logic

## Logging and Debugging

The implementation provides detailed logging to understand the transport selection:

```
[INFO] MCP server "modern-api": trying Streamable HTTP to https://api.example.com/mcp
[INFO] MCP server "modern-api": successfully connected using Streamable HTTP

[INFO] MCP server "legacy-api": trying Streamable HTTP to https://legacy.example.com/mcp
[INFO] MCP server "legacy-api": Streamable HTTP failed with 4xx error, falling back to SSE
[WARNING] MCP server "legacy-api": Using SSE fallback (deprecated), server should support Streamable HTTP
[INFO] MCP server "legacy-api": successfully connected using SSE fallback

[INFO] MCP server "explicit-sse": connecting via SSE (explicit) to https://old.example.com/mcp/sse
[WARNING] MCP server "explicit-sse": SSE transport is deprecated, consider migrating to streamable_http
```

## Migration Guide

### For Users

1. **No Action Required**: Auto-detection works with both new and old servers
2. **Remove Explicit SSE**: Remove `"transport": "sse"` to enable auto-detection
3. **Monitor Warnings**: Watch for deprecation warnings in logs

### For Server Developers

1. **Add Streamable HTTP Support**: Implement MCP 2025-03-26 Streamable HTTP transport
2. **Maintain SSE Compatibility**: Keep SSE for backwards compatibility during transition
3. **Return Proper 4xx Errors**: Ensure unsupported methods return 405 Method Not Allowed

## Error Handling

### 4xx Errors (Trigger Fallback)
- 400 Bad Request → fallback to SSE
- 404 Not Found → fallback to SSE  
- 405 Method Not Allowed → fallback to SSE
- Other 4xx status codes → fallback to SSE

### Non-4xx Errors (No Fallback)
- Network connectivity issues → re-thrown
- 5xx server errors → re-thrown
- Timeout errors → re-thrown
- DNS resolution failures → re-thrown

## Testing the Implementation

### Test Auto-Detection

```python
# This will try Streamable HTTP first, fallback to SSE on 4xx
config = {
    "test-server": {
        "url": "https://your-server.com/mcp",
        "headers": {"Authorization": "Bearer test_token"}
    }
}

tools, cleanup = await convert_mcp_to_langchain_tools(config)
# Check logs to see which transport was used
```

### Test Explicit Transports

```python
# Force Streamable HTTP (no fallback)
config_streamable = {
    "test-server": {
        "url": "https://your-server.com/mcp", 
        "transport": "streamable_http"
    }
}

# Force SSE (with deprecation warning)
config_sse = {
    "test-server": {
        "url": "https://your-server.com/mcp/sse",
        "transport": "sse"
    }
}
```

## Comparison with TypeScript Version

| Feature | Python Implementation | TypeScript Implementation | Status |
|---------|----------------------|---------------------------|--------|
| Auto-detection | ✅ Streamable HTTP → SSE fallback | ✅ Streamable HTTP → SSE fallback | ✅ Aligned |
| 4xx Error Detection | ✅ Multiple patterns | ✅ Multiple patterns | ✅ Aligned |
| Transport Keywords | ✅ `streamable_http` | ✅ `streamable_http` | ✅ Aligned |
| Deprecation Warnings | ✅ SSE shows warnings | ✅ SSE shows warnings | ✅ Aligned |
| Connection-Level Fallback | ✅ Full connection test | ✅ Full connection test | ✅ Aligned |
| Logging Detail | ✅ Detailed transport logs | ✅ Detailed transport logs | ✅ Aligned |

## Advanced Configuration

### Custom Timeout for Fallback

```python
config = {
    "slow-server": {
        "url": "https://slow.example.com/mcp",
        "timeout": 120.0,  # Longer timeout for slow servers
        "headers": {"Authorization": "Bearer token"}
    }
}
```

### Authentication with Both Transports

```python
config = {
    "auth-server": {
        "url": "https://secure.example.com/mcp",
        "headers": {
            "Authorization": "Bearer token123",
            "X-API-Key": "key456"
        }
    }
}
# Headers will be used for both Streamable HTTP attempt and SSE fallback
```

## Future Considerations

1. **Server Migration Tracking**: Monitor logs to identify servers needing Streamable HTTP support
2. **Performance Analysis**: Compare Streamable HTTP vs SSE performance in your environment  
3. **Spec Updates**: Stay current with MCP specification updates
4. **Deprecation Timeline**: Plan for eventual SSE removal based on server ecosystem migration

## Troubleshooting

### Issue: No Fallback Occurring
- **Check**: Server returns proper 4xx status codes for unsupported methods
- **Verify**: URL is correct for both Streamable HTTP and SSE attempts
- **Test**: Try explicit transports to isolate the issue

### Issue: Unexpected Transport Used
- **Review**: Logs show detailed transport selection reasoning
- **Verify**: Configuration doesn't have conflicting settings
- **Test**: Use explicit `transport` field to override auto-detection

### Issue: Authentication Failures
- **Check**: Headers are properly configured for both transport types
- **Verify**: Server accepts same authentication for both transports
- **Test**: Try explicit transports with authentication separately
