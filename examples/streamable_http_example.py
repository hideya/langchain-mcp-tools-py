#!/usr/bin/env python3
"""
Example demonstrating MCP specification-compliant Streamable HTTP transport support.

This example shows the correct implementation of MCP 2025-03-26 backwards compatibility:
1. Auto-detection: Try Streamable HTTP first, fallback to SSE on 4xx errors
2. Explicit transport selection when needed
3. Proper error handling and logging
4. Alignment with TypeScript langchain-mcp-tools implementation
"""

import asyncio
import logging
from langchain_mcp_tools import convert_mcp_to_langchain_tools

# Configure logging to see transport selection and fallback behavior
logging.basicConfig(level=logging.INFO)

async def main():
    """Demonstrate MCP specification-compliant transport handling."""
    
    # Example 1: Auto-Detection (MCP Spec Recommended)
    # This follows the MCP 2025-03-26 backwards compatibility guidelines
    auto_detection_configs = {
        "modern-server": {
            "url": "https://api.example.com/mcp",
            # No transport specified - implements MCP spec auto-detection:
            # 1. Try Streamable HTTP first
            # 2. On 4xx error → fallback to SSE
            # 3. Non-4xx errors → re-thrown
            "headers": {"Authorization": "Bearer token123"},
            "timeout": 60.0
        },
        
        "unknown-server": {
            "url": "https://unknown.example.com/mcp",
            # Will automatically detect the best transport
            "headers": {"Authorization": "Bearer token456"}
        }
    }
    
    # Example 2: Explicit Transports (when you know what the server supports)
    explicit_configs = {
        "guaranteed-streamable": {
            "url": "https://modern.example.com/mcp",
            "transport": "streamable_http",  # No fallback, direct connection
            "headers": {"Authorization": "Bearer modern_token"}
        },
        
        "legacy-only": {
            "url": "https://legacy.example.com/mcp/sse", 
            "transport": "sse",  # Explicit SSE, shows deprecation warning
            "headers": {"Authorization": "Bearer legacy_token"}
        }
    }
    
    # Example 3: Mixed Production Configuration
    production_configs = {
        # Local development servers
        "filesystem": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "."]
        },
        
        "fetch": {
            "command": "uvx", 
            "args": ["mcp-server-fetch"]
        },
        
        # Remote servers with auto-detection (recommended)
        "primary-api": {
            "url": "https://api.acme.com/mcp",
            # Auto-detects: Streamable HTTP → SSE fallback per MCP spec
            "headers": {"Authorization": "Bearer prod_token_123"},
            "timeout": 30.0
        },
        
        "partner-api": {
            "url": "https://partner.acme.com/mcp",
            # Also auto-detects for maximum compatibility
            "headers": {
                "Authorization": "Bearer partner_token_456",
                "X-Partner-ID": "acme-corp"
            }
        },
        
        # Known legacy server (explicit)
        "legacy-integration": {
            "url": "https://old-system.acme.com/mcp/sse",
            "transport": "sse",  # Explicit because we know it's legacy
            "headers": {"Authorization": "Bearer legacy_token_789"}
        },
        
        # WebSocket server
        "realtime-server": {
            "url": "wss://realtime.acme.com/mcp",
            "transport": "websocket"
        }
    }
    
    print("🚀 Demonstrating MCP Spec-Compliant Streamable HTTP Support")
    print("=" * 70)
    
    # Note: These examples use placeholder URLs that won't actually work
    # In practice, you'd replace these with real MCP server endpoints
    
    try:
        print("\n📡 Example 1: MCP Spec Auto-Detection (Recommended)")
        print("This follows MCP 2025-03-26 backwards compatibility guidelines:")
        print("• Try Streamable HTTP first") 
        print("• Fallback to SSE on 4xx errors")
        print("• Re-throw non-4xx errors")
        # tools, cleanup = await convert_mcp_to_langchain_tools(auto_detection_configs)
        # print(f"✅ Connected with {len(tools)} tools")
        # await cleanup()
        
        print("\n⚡ Example 2: Explicit Transport Selection")
        print("Use when you know exactly what the server supports:")
        # tools, cleanup = await convert_mcp_to_langchain_tools(explicit_configs)
        # print(f"✅ Connected with {len(tools)} tools")
        # await cleanup()
        
        print("\n🏭 Example 3: Production Mixed Configuration")
        print("Real-world setup with local + remote servers:")
        # tools, cleanup = await convert_mcp_to_langchain_tools(production_configs)
        # print(f"✅ Connected with {len(tools)} tools total")
        # await cleanup()
        
        print("\n✨ MCP Specification Compliance:")
        print("• HTTP URLs: Auto-detection (Streamable HTTP → SSE fallback)")
        print("• WebSocket URLs: Direct WebSocket connection")
        print("• Command configs: stdio transport")
        print("• Explicit transport always respected")
        
        print("\n🔄 Fallback Behavior (per MCP spec):")
        print("1. POST InitializeRequest to server URL")
        print("2. Success → Streamable HTTP transport")
        print("3. 4xx error → GET request for SSE stream")
        print("4. Non-4xx error → re-thrown (network issues)")
        
    except Exception as e:
        print(f"❌ Error (expected with placeholder URLs): {e}")
    
    print("\n📋 Migration Benefits:")
    print("✅ No configuration changes needed for most users")
    print("✅ Automatic compatibility with new and old servers") 
    print("✅ Clear deprecation warnings guide future migration")
    print("✅ Full alignment with TypeScript implementation")
    
    print("\n🔍 Log Messages to Watch For:")
    print('• "trying Streamable HTTP" → Initial attempt')
    print('• "successfully connected using Streamable HTTP" → Modern server')
    print('• "falling back to SSE" → Legacy server detected')
    print('• "SSE transport is deprecated" → Migration needed')

if __name__ == "__main__":
    asyncio.run(main())
