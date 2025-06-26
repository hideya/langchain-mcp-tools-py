
def validate_mcp_server_config(
    server_name: str,
    server_config: SingleMcpServerConfig,
    logger: logging.Logger
) -> None:
    """Validates MCP server configuration following TypeScript transport selection logic.
    
    Transport Selection Priority:
    1. Explicit transport/type field (must match URL protocol if URL provided)
    2. URL protocol auto-detection (http/https → StreamableHTTP, ws/wss → WebSocket)
    3. Command presence → Stdio transport
    4. Error if none of the above match
    
    Conflicts that cause errors:
    - Both url and command specified
    - transport/type doesn't match URL protocol
    - transport requires URL but no URL provided
    - transport requires command but no command provided
    
    Args:
        server_name: Server instance name for error messages
        server_config: Configuration to validate
        logger: Logger for warnings
        
    Raises:
        ValueError: If configuration is invalid
    """
    has_url = "url" in server_config and server_config["url"] is not None
    has_command = "command" in server_config and server_config["command"] is not None
    
    # Get transport type (prefer 'transport' over 'type' for compatibility)
    transport_type = server_config.get("transport") or server_config.get("type")
    
    # Conflict check: Both url and command specified
    if has_url and has_command:
        raise ValueError(
            f'MCP server "{server_name}": Cannot specify both "url" ({server_config["url"]}) '
            f'and "command" ({server_config["command"]}). Use "url" for remote servers '
            f'or "command" for local servers.'
        )
    
    # Must have either URL or command
    if not has_url and not has_command:
        raise ValueError(
            f'MCP server "{server_name}": Either "url" or "command" must be specified'
        )
    
    if has_url:
        url_str = str(server_config["url"])
        try:
            parsed_url = urlparse(url_str)
            url_scheme = parsed_url.scheme.lower()
        except Exception:
            raise ValueError(
                f'MCP server "{server_name}": Invalid URL format: {url_str}'
            )
        
        if transport_type:
            transport_lower = transport_type.lower()
            
            # Check transport/URL protocol compatibility
            if transport_lower in ["http", "streamable_http"] and url_scheme not in ["http", "https"]:
                raise ValueError(
                    f'MCP server "{server_name}": Transport "{transport_type}" requires '
                    f'http:// or https:// URL, but got: {url_scheme}://'
                )
            elif transport_lower == "sse" and url_scheme not in ["http", "https"]:
                raise ValueError(
                    f'MCP server "{server_name}": Transport "sse" requires '
                    f'http:// or https:// URL, but got: {url_scheme}://'
                )
            elif transport_lower in ["ws", "websocket"] and url_scheme not in ["ws", "wss"]:
                raise ValueError(
                    f'MCP server "{server_name}": Transport "{transport_type}" requires '
                    f'ws:// or wss:// URL, but got: {url_scheme}://'
                )
            elif transport_lower == "stdio":
                raise ValueError(
                    f'MCP server "{server_name}": Transport "stdio" requires "command", '
                    f'but "url" was provided'
                )
        
        # Validate URL scheme is supported
        if url_scheme not in ["http", "https", "ws", "wss"]:
            raise ValueError(
                f'MCP server "{server_name}": Unsupported URL scheme "{url_scheme}". '
                f'Supported schemes: http, https, ws, wss'
            )
    
    elif has_command:
        if transport_type:
            transport_lower = transport_type.lower()
            
            # Check transport requires command
            if transport_lower == "stdio":
                pass  # Valid
            elif transport_lower in ["http", "streamable_http", "sse", "ws", "websocket"]:
                raise ValueError(
                    f'MCP server "{server_name}": Transport "{transport_type}" requires "url", '
                    f'but "command" was provided'
                )
            else:
                logger.warning(
                    f'MCP server "{server_name}": Unknown transport type "{transport_type}", '
                    f'treating as stdio'
                )

