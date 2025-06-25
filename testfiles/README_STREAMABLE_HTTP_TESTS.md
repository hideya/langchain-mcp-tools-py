# StreamableHTTP Test Files for MCP Python Library

This directory contains test implementations for the StreamableHTTP transport in the MCP Python library, equivalent to the TypeScript versions in the TS library.

## Files Overview

### Stateless StreamableHTTP
- `streamable-http-stateless-test-server.py` - Stateless StreamableHTTP server using FastMCP
- `streamable-http-stateless-test-client.py` - Client to test stateless server

### Authenticated StreamableHTTP  
- `streamable-http-auth-test-server.py` - StreamableHTTP server with basic auth using FastMCP
- `streamable-http-auth-test-client.py` - Client to test authenticated server

## Usage

### Testing Stateless StreamableHTTP

1. **Start the stateless server:**
   ```bash
   uv run testfiles/streamable-http-stateless-test-server.py
   ```

2. **In another terminal, run the client:**
   ```bash
   uv run testfiles/streamable-http-stateless-test-client.py
   ```

### Testing Authenticated StreamableHTTP

1. **Start the auth server:**
   ```bash
   uv run testfiles/streamable-http-auth-test-server.py
   ```

2. **In another terminal, run the client:**
   ```bash
   uv run testfiles/streamable-http-auth-test-client.py
   ```

## What These Tests Demonstrate

### Stateless Server Benefits
- ✅ No session management required
- ✅ Each request completely isolated  
- ✅ Horizontally scalable
- ✅ Simple deployment
- ✅ No memory leaks from accumulated state
- ✅ Concurrent connections work seamlessly

### Authentication Features
- ✅ Bearer token authentication
- ✅ Explicit StreamableHTTP transport
- ✅ Transport auto-detection
- ✅ Authenticated tool execution
- ✅ Proper connection cleanup

## Server Endpoints

### Stateless Server (Port 3335)
- **Root:** `http://127.0.0.1:3335/`
- **MCP:** `http://127.0.0.1:3335/mcp`
- **Tools:** `echo`, `server-info`, `random-number`

### Auth Server (Port 3334)
- **Root:** `http://127.0.0.1:3334/`
- **MCP:** `http://127.0.0.1:3334/mcp` 
- **Token:** `http://127.0.0.1:3334/token`
- **Tools:** `echo`, `server-info` (both require auth)

## Implementation Notes

### Stateless Server
- Uses `FastMCP` with `stateless_http=True`
- Each request creates new server instance
- No session state maintained
- Prevents request ID collisions

### Auth Server  
- Uses simplified Bearer token auth (⚠️ **NOT OAuth 2.1 compliant**)
- Custom authentication middleware
- Global auth state for tool access
- For **testing purposes only**

### Client Library Integration
- Uses your `langchain_mcp_tools` library
- Tests both explicit transport and auto-detection
- Demonstrates concurrent connection handling
- Proper cleanup with async context managers

## Transport Auto-Detection

The clients test the MCP specification's transport auto-detection:

1. **Try StreamableHTTP first** - POST InitializeRequest to URL
2. **Fallback to SSE on 4xx** - If server returns 4xx error
3. **Explicit transport** - Override auto-detection when specified

This ensures maximum compatibility with both new and legacy servers.

## Security Warning

⚠️ **The authentication implementation is for TESTING ONLY**

The auth server does NOT implement proper OAuth 2.1 security:
- ❌ No PKCE (required in OAuth 2.1)
- ❌ No proper authorization flow
- ❌ Hardcoded tokens (security risk)
- ❌ No real token validation

For production, implement proper OAuth 2.1 with:
- ✅ PKCE (Proof Key for Code Exchange)
- ✅ Authorization Code Flow
- ✅ Secure token storage and validation
- ✅ Dynamic Client Registration

## Troubleshooting

### Server Won't Start
- Check if ports 3334/3335 are available
- Ensure all dependencies are installed with `uv`
- Check for any import errors in console

### Client Connection Fails
- Verify server is running first
- Check network connectivity  
- Look for authentication errors (auth server)
- Ensure token format is correct (auth server)

### Transport Detection Issues
- Enable debug logging in client
- Check if server supports StreamableHTTP
- Verify fallback to SSE works for legacy servers

## Comparing with TypeScript

These Python implementations mirror the TypeScript versions:

| TypeScript | Python | Purpose |
|------------|--------|---------|
| `streamable-http-stateless-test-server.ts` | `streamable-http-stateless-test-server.py` | Stateless server |
| `streamable-http-stateless-test-client.ts` | `streamable-http-stateless-test-client.py` | Stateless client |
| `streamable-http-auth-test-server.ts` | `streamable-http-auth-test-server.py` | Auth server |
| `streamable-http-auth-test-client.ts` | `streamable-http-auth-test-client.py` | Auth client |

The implementations follow the same patterns and test the same scenarios, ensuring consistency between the TypeScript and Python versions of your library.
