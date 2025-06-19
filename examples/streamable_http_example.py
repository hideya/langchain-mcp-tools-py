#!/usr/bin/env python3
"""
Example demonstrating Streamable HTTP transport support in langchain-mcp-tools.

This example shows:
1. How to configure different transport types
2. The new streamable_http default behavior
3. Backward compatibility with SSE
4. Migration patterns from SSE to Streamable HTTP
"""

import asyncio
import logging
from langchain_mcp_tools import convert_mcp_to_langchain_tools

# Configure logging to see transport selection and deprecation warnings
logging.basicConfig(level=logging.INFO)

async def main():
    """Demonstrate different transport configurations."""
    
    # Example 1: Streamable HTTP (recommended, default for HTTP/HTTPS)
    streamable_http_configs = {
        "modern-api": {
            "url": "https://api.example.com/mcp",
            # transport: "streamable_http" is now the default for HTTP/HTTPS URLs
            "headers": {"Authorization": "Bearer token123"},
            "timeout": 60.0
        },
        
        "explicit-streamable": {
            "url": "https://api2.example.com/mcp",
            "transport": "streamable_http",  # Explicit (but optional)
            "headers": {"Authorization": "Bearer token456"}
        }
    }
    
    # Example 2: Legacy SSE (deprecated, shows warnings)
    legacy_sse_configs = {
        "legacy-server": {
            "url": "https://legacy.example.com/mcp/sse",
            "transport": "sse",  # Must be explicit now
            "headers": {"Authorization": "Bearer legacy_token"}
        }
    }
    
    # Example 3: Mixed configuration (recommended pattern)
    mixed_configs = {
        # Local development servers
        "filesystem": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "."]
        },
        
        "fetch": {
            "command": "uvx",
            "args": ["mcp-server-fetch"]
        },
        
        # Production Streamable HTTP server (default)
        "production-api": {
            "url": "https://prod-api.example.com/mcp",
            "headers": {"Authorization": "Bearer prod_token"},
            "timeout": 30.0
        },
        
        # Legacy SSE server (explicit)
        "legacy-integration": {
            "url": "https://partner.example.com/mcp/sse",
            "transport": "sse",
            "headers": {"Authorization": "Bearer partner_token"}
        },
        
        # WebSocket server
        "realtime-server": {
            "url": "wss://realtime.example.com/mcp",
            "transport": "websocket"
        }
    }
    
    print("🚀 Demonstrating Streamable HTTP support...")
    print("=" * 60)
    
    # Note: These examples use placeholder URLs that won't actually work
    # In practice, you'd replace these with real MCP server endpoints
    
    try:
        print("\n📡 Example 1: Streamable HTTP (Default)")
        print("This will use streamable_http transport by default for HTTP URLs")
        # tools, cleanup = await convert_mcp_to_langchain_tools(streamable_http_configs)
        # print(f"✅ Connected with {len(tools)} tools")
        # await cleanup()
        
        print("\n⚠️  Example 2: Legacy SSE (Deprecated)")
        print("This will show deprecation warnings for SSE transport")
        # tools, cleanup = await convert_mcp_to_langchain_tools(legacy_sse_configs)
        # print(f"✅ Connected with {len(tools)} tools (with warnings)")
        # await cleanup()
        
        print("\n🔄 Example 3: Mixed Configuration")
        print("This demonstrates the recommended pattern for production use")
        # tools, cleanup = await convert_mcp_to_langchain_tools(mixed_configs)
        # print(f"✅ Connected with {len(tools)} tools total")
        # await cleanup()
        
        print("\n✨ Transport Selection Logic:")
        print("- HTTP/HTTPS URLs: streamable_http (default) > sse (explicit)")
        print("- WS/WSS URLs: websocket")
        print("- Commands: stdio")
        print("- Explicit transport setting always takes precedence")
        
    except Exception as e:
        print(f"❌ Error (expected with placeholder URLs): {e}")
    
    print("\n📋 Migration Guide:")
    print("1. Remove explicit 'sse' transport from configs (use default)")
    print("2. Update server endpoints to support Streamable HTTP")
    print("3. Test configurations and monitor logs for deprecation warnings")
    print("4. Update documentation to reflect new defaults")

if __name__ == "__main__":
    asyncio.run(main())
