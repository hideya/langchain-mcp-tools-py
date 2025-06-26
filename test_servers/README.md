# Test Servers for langchain-mcp-tools Streamable HTTP Support

This directory contains simple test servers to validate your streamable HTTP implementation.

## Files

### 1. `simple_stateless_server.py`
A minimal stateless MCP server using FastMCP.run():
- **Transport**: Streamable HTTP (stateless, JSON responses only)
- **Endpoint**: `http://localhost:8000/mcp` (default port)
- **Tools**: add, multiply, greet, echo, factorial
- **Resources**: server info

**Usage:**
```bash
python simple_stateless_server.py
```

### 1b. `simple_stateless_server_uvicorn.py`
Same server but using uvicorn directly for more control:
- **Benefits**: Custom host/port, more uvicorn options
- **Usage**: `python simple_stateless_server_uvicorn.py`

### 2. `multi_server_fastapi.py`
Multiple stateless MCP servers in a single FastAPI application:
- **Echo Server**: `/echo/mcp` - Text manipulation tools
- **Math Server**: `/math/mcp` - Mathematical operations  
- **Utils Server**: `/utils/mcp` - Utility functions
- **Health Check**: `/health`
- **Server Info**: `/`

**Usage:**
```bash
python multi_server_fastapi.py
```

### 3. `test_client.py`
Test client using your `langchain-mcp-tools` library:
- Tests transport auto-detection
- Validates tool execution
- Demonstrates mixed configurations
- **Works with both single and multi-server setups**

**Usage:**
```bash
# Start a server first, then:
python test_client.py
```

### 4. `curl_test.py`
Manual curl tests for **single-server setup**:
- Tests single endpoint: `http://localhost:8000/mcp`
- **Use with**: `simple_stateless_server.py`

**Usage:**
```bash
python simple_stateless_server.py  # Start single server
python curl_test.py                # Test single endpoint
```

### 5. `curl_test_multi.py`
Manual curl tests for **multi-server setup**:
- Tests multiple endpoints: `/echo/mcp`, `/math/mcp`, `/utils/mcp`
- **Use with**: `multi_server_fastapi.py`

**Usage:**
```bash
python multi_server_fastapi.py     # Start multi-server
python curl_test_multi.py          # Test all endpoints
```

### 6. `simple_bearer_auth_server.py`
MCP server with bearer token authentication:
- **Authentication**: `Authorization: Bearer <token>` header
- **Endpoint**: `http://localhost:8001/mcp`
- **Test tokens**: `valid-token-123`, `read-only-token`, `expired-token`, etc.
- **Purpose**: Test your library's `headers` authentication support

**Usage:**
```bash
python simple_bearer_auth_server.py  # Start auth server
python test_auth_client.py           # Test auth scenarios
```

### 7. `api_key_auth_server.py`
MCP server with API key authentication:
- **Authentication**: `X-API-Key: <key>` header
- **Endpoint**: `http://localhost:8002/mcp`
- **Test keys**: `sk-test-key-123`, `sk-demo-key-456`, etc.
- **Features**: Rate limiting, different user plans

**Usage:**
```bash
python api_key_auth_server.py        # Start API key auth server
```

### 8. `test_auth_client.py`
Basic authentication test client:
- Tests bearer token authentication
- Tests various auth scenarios (valid/invalid/missing)
- Validates tool execution with auth

### 9. `test_comprehensive_auth.py`
Comprehensive authentication test suite:
- Tests bearer token + API key authentication
- Tests mixed authentication servers
- Tests custom headers functionality
- Tests edge cases and error scenarios

**Usage:**
```bash
# Start both auth servers:
python simple_bearer_auth_server.py  # Port 8001
python api_key_auth_server.py        # Port 8002

# Run comprehensive tests:
python test_comprehensive_auth.py
```

### 10. `simple_oauth_server.py`
MCP server with OAuth 2.0 authentication:
- **Authentication**: OAuth 2.0 Authorization Code Flow
- **Endpoint**: `http://localhost:8003/mcp`
- **OAuth Endpoints**: `/authorize`, `/token`, `/.well-known/oauth-authorization-server`
- **Purpose**: Test your library's `auth` parameter support
- **Features**: Full OAuth 2.0 server with authorization and token endpoints

**Usage:**
```bash
python simple_oauth_server.py        # Start OAuth server
python test_oauth_client.py          # Test OAuth flow
```

### 11. `test_oauth_client.py`
OAuth authentication test client:
- Tests OAuth 2.0 authorization code flow
- Tests browser-based authorization
- Tests access token usage for MCP requests
- Tests error scenarios
- Demonstrates `auth` parameter usage with `OAuthClientProvider`

**Usage:**
```bash
# Start OAuth server first:
python simple_oauth_server.py        # Port 8003

# Run OAuth tests (browser will open):
python test_oauth_client.py
```

## Testing Your Implementation

1. **Start a test server:**
   ```bash
   cd test_servers
   python simple_stateless_server.py
   ```

2. **Test with curl:**
   ```bash
   # Initialize connection
   curl -X POST http://localhost:8000/mcp \
        -H "Content-Type: application/json" \
        -H "Accept: application/json" \
        -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0.0"}}}'
   
   # List tools
   curl -X POST http://localhost:8000/mcp \
        -H "Content-Type: application/json" \
        -H "Accept: application/json" \
        -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
   ```

3. **Test with your library:**
   ```bash
   python test_client.py
   ```

4. **Test authentication:**
   ```bash
   # Basic auth test:
   python simple_bearer_auth_server.py  # Terminal 1
   python test_auth_client.py           # Terminal 2
   
   # Comprehensive auth test:
   python simple_bearer_auth_server.py  # Terminal 1 (port 8001)
   python api_key_auth_server.py        # Terminal 2 (port 8002)
   python test_comprehensive_auth.py    # Terminal 3
   
   # OAuth test (browser will open):
   python simple_oauth_server.py        # Terminal 1 (port 8003)
   python test_oauth_client.py          # Terminal 2
   ```

## Expected Behavior

### Transport Auto-Detection
Your library should:
1. Try Streamable HTTP first (POST initialize request)
2. Succeed immediately (no fallback needed)
3. Log: `"detected Streamable HTTP transport support"`

### Tool Execution
All tools should work correctly through your LangChain integration:
- Mathematical operations (add, multiply, etc.)
- Text manipulation (echo, reverse, etc.)
- Utility functions (UUID generation, email validation, etc.)

### Error Handling
- Connection errors should be properly reported
- Tool execution errors should be handled gracefully
- Cleanup should occur automatically

## MCP Specification Compliance

These servers follow MCP 2025-03-26 specification:
- ✅ Single `/mcp` endpoint for POST and GET
- ✅ Proper Content-Type and Accept headers
- ✅ JSON-RPC 2.0 message format
- ✅ Stateless operation (no session persistence)
- ✅ CORS and Origin validation
- ✅ HTTP 202 Accepted responses for POST requests

## Troubleshooting

### Connection Issues
- Ensure the server is running on the expected port
- Check firewall settings
- Verify the URL is correct (`http://localhost:8000/mcp`)

### Transport Detection Issues
- Check logs for "trying Streamable HTTP" messages
- Ensure Accept header includes `application/json`
- Verify your auto-detection logic handles 200 responses correctly

### Tool Execution Issues
- Verify tools are listed correctly
- Check parameter schemas match expected formats
- Ensure error responses are properly formatted

### 307 Redirect Messages (Multi-Server Setup)
- You may see `INFO: 127.0.0.1:xxxxx - "POST /path/mcp HTTP/1.1" 307 Temporary Redirect` in server logs
- This is **normal FastAPI behavior** for URL consistency (redirects `/path` to `/path/`)
- The requests still succeed after the automatic redirect
- No action needed - this indicates proper FastAPI operation
