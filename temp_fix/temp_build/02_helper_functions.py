
def is_4xx_error(error: Exception) -> bool:
    """Enhanced 4xx error detection matching TypeScript implementation.
    
    Used to decide whether to fall back from Streamable HTTP to SSE transport
    per MCP specification. Handles various error types and patterns that indicate
    4xx-like conditions.
    
    Args:
        error: The error to check
        
    Returns:
        True if the error represents a 4xx HTTP status or equivalent
    """
    if not error:
        return False
    
    # Handle ExceptionGroup (Python 3.11+) by checking sub-exceptions
    if hasattr(error, 'exceptions'):
        return any(is_4xx_error(sub_error) for sub_error in error.exceptions)
    
    # Check for explicit HTTP status codes
    if hasattr(error, 'status') and isinstance(error.status, int):
        return 400 <= error.status < 500
    
    # Check for httpx response errors
    if hasattr(error, 'response') and hasattr(error.response, 'status_code'):
        return 400 <= error.response.status_code < 500
    
    # Check error message for 4xx patterns
    error_str = str(error).lower()
    
    # Look for specific 4xx status codes (enhanced pattern matching)
    if any(code in error_str for code in ['400', '401', '402', '403', '404', '405', '406', '407', '408', '409']):
        return True
    
    # Look for 4xx error names (expanded list matching TypeScript version)
    return any(pattern in error_str for pattern in [
        'bad request',
        'unauthorized',
        'forbidden', 
        'not found',
        'method not allowed',
        'not acceptable',
        'request timeout',
        'conflict'
    ])


async def test_streamable_http_support(
    url: str, 
    headers: dict[str, str] | None = None,
    timeout: float = 30.0,
    auth: httpx.Auth | None = None,
    logger: logging.Logger = logging.getLogger(__name__)
) -> bool:
    """Test if URL supports Streamable HTTP per official MCP specification.
    
    Follows the MCP specification's recommended approach for backwards compatibility.
    Uses proper InitializeRequest with official protocol version and required headers.
    
    See: https://modelcontextprotocol.io/specification/2025-03-26/basic/transports#backwards-compatibility
    
    Args:
        url: The MCP server URL to test
        headers: Optional HTTP headers
        timeout: Request timeout
        auth: Optional httpx authentication
        logger: Logger for debugging
        
    Returns:
        True if Streamable HTTP is supported, False if should fallback to SSE
        
    Raises:
        Exception: For non-4xx errors that should be re-raised
    """
    # Create InitializeRequest as per MCP specification
    init_request = {
        "jsonrpc": "2.0",
        "id": f"transport-test-{int(time.time() * 1000)}",  # Use milliseconds like TS version
        "method": "initialize", 
        "params": {
            "protocolVersion": "2024-11-05",  # Official MCP Protocol version
            "capabilities": {},
            "clientInfo": {
                "name": "mcp-transport-test",
                "version": "1.0.0"
            }
        }
    }
    
    # Required headers per MCP specification
    request_headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/event-stream'  # Required by spec
    }
    if headers:
        request_headers.update(headers)
    
    try:
        async with httpx.AsyncClient() as client:
            logger.debug(f"Testing Streamable HTTP: POST InitializeRequest to {url}")
            response = await client.post(
                url,
                json=init_request,
                headers=request_headers,
                timeout=timeout,
                auth=auth
            )
            
            logger.debug(f"Transport test response: {response.status_code} {response.headers.get('content-type', 'N/A')}")
            
            if response.status_code == 200:
                # Success indicates Streamable HTTP support
                logger.debug("Streamable HTTP test successful")
                return True
            elif 400 <= response.status_code < 500:
                # 4xx error indicates fallback to SSE per MCP spec
                logger.debug(f"Received {response.status_code}, should fallback to SSE")
                return False
            else:
                # Other errors should be re-raised
                response.raise_for_status()
                return True  # If we get here, it succeeded
                
    except httpx.TimeoutException:
        logger.debug("Request timeout - treating as connection error")
        raise
    except httpx.ConnectError:
        logger.debug("Connection error")
        raise
    except Exception as e:
        # Check if it's a 4xx-like error using improved detection
        if is_4xx_error(e):
            logger.debug(f"4xx-like error detected: {e}")
            return False
        raise

