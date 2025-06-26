
async def spawn_mcp_server_and_get_transport(
    server_name: str,
    server_config: SingleMcpServerConfig,
    exit_stack: AsyncExitStack,
    logger: logging.Logger = logging.getLogger(__name__)
) -> Transport:
    """Spawns an MCP server process and establishes communication channels.

    Implements consistent transport selection logic matching TypeScript version:
    
    Transport Selection Priority:
    1. Explicit transport/type field (must match URL protocol if URL provided)
    2. URL protocol auto-detection (http/https → StreamableHTTP, ws/wss → WebSocket)
    3. Command presence → Stdio transport
    4. Error if none of the above match
    
    For HTTP URLs without explicit transport, follows MCP specification backwards
    compatibility: try Streamable HTTP first, fallback to SSE on 4xx errors.

    Supports multiple transport types:
    - stdio: For local command-based servers
    - streamable_http, http: For Streamable HTTP servers
    - sse: For Server-Sent Events HTTP servers (legacy)
    - websocket, ws: For WebSocket servers

    Args:
        server_name: Server instance name to use for better logging
        server_config: Configuration dictionary for server setup
        exit_stack: Context manager for cleanup handling
        logger: Logger instance for debugging and monitoring

    Returns:
        A tuple of receive and send streams for server communication

    Raises:
        ValueError: If configuration is invalid
        Exception: If server spawning fails
    """
    try:
        logger.info(f'MCP server "{server_name}": '
                    f"initializing with: {server_config}")

        # Validate configuration first
        validate_mcp_server_config(server_name, server_config, logger)
        
        # Determine if URL-based or command-based
        has_url = "url" in server_config and server_config["url"] is not None
        has_command = "command" in server_config and server_config["command"] is not None
        
        # Get transport type (prefer 'transport' over 'type')
        transport_type = server_config.get("transport") or server_config.get("type")
        
        if has_url:
            # URL-based configuration
            url_config = cast(McpServerUrlBasedConfig, server_config)
            url_str = str(url_config["url"])
            parsed_url = urlparse(url_str)
            url_scheme = parsed_url.scheme.lower()
            
            # Extract common parameters
            headers = url_config.get("headers", None)
            timeout = url_config.get("timeout", None)
            auth = url_config.get("auth", None)
            
            if url_scheme in ["http", "https"]:
                # HTTP/HTTPS: Handle explicit transport or auto-detection
                
                if transport_type and transport_type.lower() in ["streamable_http", "http"]:
                    # Explicit Streamable HTTP (no fallback)
                    logger.info(f'MCP server "{server_name}": '
                               f"connecting via Streamable HTTP (explicit) to {url_str}")
                    
                    kwargs = {}
                    if headers is not None:
                        kwargs["headers"] = headers
                    if timeout is not None:
                        kwargs["timeout"] = timeout
                    if auth is not None:
                        kwargs["auth"] = auth
                    
                    transport = await exit_stack.enter_async_context(
                        streamablehttp_client(url_str, **kwargs)
                    )
                    
                elif transport_type and transport_type.lower() == "sse":
                    # Explicit SSE (no fallback)
                    logger.info(f'MCP server "{server_name}": '
                               f"connecting via SSE (explicit) to {url_str}")
                    logger.warning(f'MCP server "{server_name}": '
                                  f"SSE transport is deprecated, consider migrating to streamable_http")
                    
                    transport = await exit_stack.enter_async_context(
                        sse_client(url_str, headers=headers)
                    )
                    
                else:
                    # Auto-detection: URL protocol suggests HTTP transport, try Streamable HTTP first
                    logger.debug(f'MCP server "{server_name}": '
                                f"auto-detecting HTTP transport using MCP specification method")
                    
                    try:
                        logger.info(f'MCP server "{server_name}": '
                                   f"testing Streamable HTTP support for {url_str}")
                        
                        supports_streamable = await test_streamable_http_support(
                            url_str, 
                            headers=headers,
                            timeout=timeout,
                            auth=auth,
                            logger=logger
                        )
                        
                        if supports_streamable:
                            logger.info(f'MCP server "{server_name}": '
                                       f"detected Streamable HTTP transport support")
                            
                            kwargs = {}
                            if headers is not None:
                                kwargs["headers"] = headers
                            if timeout is not None:
                                kwargs["timeout"] = timeout
                            if auth is not None:
                                kwargs["auth"] = auth
                            
                            transport = await exit_stack.enter_async_context(
                                streamablehttp_client(url_str, **kwargs)
                            )
                        else:
                            logger.info(f'MCP server "{server_name}": '
                                       f"received 4xx error, falling back to SSE transport")
                            logger.warning(f'MCP server "{server_name}": '
                                          f"Using SSE transport (deprecated), server should support Streamable HTTP")
                            
                            transport = await exit_stack.enter_async_context(
                                sse_client(url_str, headers=headers)
                            )
                            
                    except Exception as error:
                        logger.error(f'MCP server "{server_name}": '
                                    f"transport detection failed: {error}")
                        raise
                        
            elif url_scheme in ["ws", "wss"]:
                # WebSocket transport
                if transport_type and transport_type.lower() not in ["websocket", "ws"]:
                    logger.warning(f'MCP server "{server_name}": '
                                  f'URL scheme "{url_scheme}" suggests WebSocket, '
                                  f'but transport "{transport_type}" specified')
                
                logger.info(f'MCP server "{server_name}": '
                           f"connecting via WebSocket to {url_str}")
                
                transport = await exit_stack.enter_async_context(
                    websocket_client(url_str)
                )
                
            else:
                # This should be caught by validation, but include for safety
                raise ValueError(
                    f'MCP server "{server_name}": Unsupported URL scheme "{url_scheme}". '
                    f'Supported schemes: http/https (for streamable_http/sse), ws/wss (for websocket)'
                )
                
        elif has_command:
            # Command-based configuration (stdio transport)
            if transport_type and transport_type.lower() not in ["stdio", ""]:
                logger.warning(f'MCP server "{server_name}": '
                              f'Command provided suggests stdio transport, '
                              f'but transport "{transport_type}" specified')
            
            logger.info(f'MCP server "{server_name}": '
                       f"spawning local process via stdio")
            
            # NOTE: `uv` and `npx` seem to require PATH to be set.
            # To avoid confusion, it was decided to automatically append it
            # to the env if not explicitly set by the config.
            config = cast(McpServerCommandBasedConfig, server_config)
            # env = config.get("env", {}) doesn't work since it can yield None
            env_val = config.get("env")
            env = {} if env_val is None else dict(env_val)
            if "PATH" not in env:
                env["PATH"] = os.environ.get("PATH", "")

            # Use stdio client for commands
            # args = config.get("args", []) doesn't work since it can yield None
            args_val = config.get("args")
            args = [] if args_val is None else list(args_val)
            server_parameters = StdioServerParameters(
                command=config.get("command", ""),
                args=args,
                env=env,
                cwd=config.get("cwd", None)
            )

            # Initialize stdio client and register it with exit stack for cleanup
            errlog_val = config.get("errlog")
            kwargs = {"errlog": errlog_val} if errlog_val is not None else {}
            transport = await exit_stack.enter_async_context(
                stdio_client(server_parameters, **kwargs)
            )
        
        else:
            # This should be caught by validation, but include for safety
            raise ValueError(
                f'MCP server "{server_name}": Invalid configuration - '
                f'either "url" or "command" must be specified'
            )
            
    except Exception as e:
        logger.error(f'MCP server "{server_name}": error during initialization: {str(e)}')
        raise

    return transport

