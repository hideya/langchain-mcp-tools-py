Here's the key fix for your Streamable HTTP auto-detection issue:

## Problem
Your Python implementation was only doing **transport creation fallback**, while your working TypeScript version does **connection-level testing fallback**.

## Root Cause
When you use auto-detection (no explicit `"transport": "sse"`), your Python code tries Streamable HTTP first by creating the transport. But your SSE server at `/sse` expects:
- **GET** for SSE stream
- **POST** to `/message` for messages

But Streamable HTTP tries to **POST** to `/sse` for initialization, which your server doesn't support (404).

## Key Changes Needed

### 1. Fix Connection-Level Testing

Replace this section in `spawn_mcp_server_and_get_transport()`:

```python
# OLD: Only tests transport creation
try:
    transport = await exit_stack.enter_async_context(
        streamablehttp_client(url_str, **kwargs)
    )
    logger.info(f'Successfully connected using Streamable HTTP')
    
except Exception as error:
    if is_4xx_error(error):
        # Fallback to SSE...
```

With this:

```python
# NEW: Tests actual connection like TypeScript
try:
    # Create transport  
    transport = await exit_stack.enter_async_context(
        streamablehttp_client(url_str, **kwargs)
    )
    
    logger.info(f'Created Streamable HTTP transport, testing connection')
    
    # TEST THE ACTUAL CONNECTION (key difference!)
    if len(transport) == 2:
        read, write = transport
    elif len(transport) == 3:
        read, write, _ = transport
    else:
        raise ValueError(f"Unexpected transport tuple length: {len(transport)}")
    
    # Test connection by creating and initializing a session
    test_session = ClientSession(read, write)
    await test_session.initialize()
    await test_session.close()  # Clean up test session
    
    logger.info(f'Successfully connected using Streamable HTTP')
    
except Exception as error:
    logger.debug(f'Streamable HTTP connection test failed: {error}')
    logger.debug(f'Is 4xx error: {is_4xx_error(error)}')
    
    if is_4xx_error(error):
        logger.info(f'Streamable HTTP failed with 4xx error, falling back to SSE')
        
        # Create SSE transport
        transport = await exit_stack.enter_async_context(
            sse_client(url_str, headers=headers)
        )
        logger.info(f'Successfully connected using SSE fallback')
    else:
        logger.error(f'Streamable HTTP failed with non-4xx error: {error}')
        raise
```

### 2. Enhanced 4xx Error Detection

Update your `is_4xx_error()` function to be more robust:

```python
def is_4xx_error(error: Exception) -> bool:
    if not error:
        return False
    
    error_str = str(error).lower()
    
    # Check for explicit HTTP status codes
    if hasattr(error, 'status') and isinstance(error.status, int):
        return 400 <= error.status < 500
    
    # Check for httpx response errors
    if hasattr(error, 'response') and hasattr(error.response, 'status_code'):
        return 400 <= error.response.status_code < 500
    
    # Enhanced 4xx detection patterns (matching TypeScript logic)
    if any(code in error_str for code in ['400', '401', '402', '403', '404', '405', '406', '407', '408', '409']):
        return True
    
    # Check for MCP protocol errors that indicate 4xx-like conditions
    if 'session terminated' in error_str:
        return True  # Often indicates server rejected the connection
    
    # Check for common 4xx error messages  
    return (
        'bad request' in error_str or
        'unauthorized' in error_str or
        'forbidden' in error_str or
        'not found' in error_str or
        'method not allowed' in error_str
    )
```

## Expected Behavior After Fix

With the fix, you should see logs like:

```
[INFO] MCP server "weather": trying Streamable HTTP to http://localhost:56845/sse
[INFO] MCP server "weather": created Streamable HTTP transport, testing connection
[DEBUG] MCP server "weather": Streamable HTTP connection test failed: HTTP 404 Not Found
[DEBUG] MCP server "weather": Is 4xx error: True  
[INFO] MCP server "weather": Streamable HTTP failed with 4xx error, falling back to SSE
[INFO] MCP server "weather": successfully connected using SSE fallback
```

## Test the Fix

1. **Replace your current implementation** with the fixed version
2. **Remove the explicit `"transport": "sse"`** from your config:
   ```python
   "weather": {
       "url": f"http://localhost:{sse_server_port}/sse",
       # "transport": "sse",  # Remove this line
       "headers": {"Authorization": f"Bearer {bearer_token}"}
   }
   ```
3. **Run your tests** - auto-detection should now work properly

The key insight is that your TypeScript version correctly tests the **actual MCP protocol handshake**, while your Python version was only testing **transport creation**. This fix aligns them perfectly! 🎯
