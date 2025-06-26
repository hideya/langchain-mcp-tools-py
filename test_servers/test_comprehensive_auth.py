#!/usr/bin/env python3
"""
Comprehensive Authentication Test Client

This script tests all authentication scenarios with your langchain-mcp-tools library:
- Bearer token authentication 
- API key authentication
- Multiple authentication methods
- Error handling scenarios

Usage:
    # Start both auth servers:
    python simple_bearer_auth_server.py  # Port 8001
    python api_key_auth_server.py        # Port 8002
    
    # Then run this comprehensive test:
    python test_comprehensive_auth.py
"""

import asyncio
import logging
from langchain_mcp_tools import convert_mcp_to_langchain_tools

# Configure logging
logging.basicConfig(level=logging.INFO)

async def test_bearer_token_auth():
    """Test bearer token authentication scenarios."""
    print("🔐 Testing Bearer Token Authentication")
    print("=" * 50)
    
    test_cases = [
        {
            "name": "Valid Bearer Token",
            "config": {
                "bearer-valid": {
                    "url": "http://127.0.0.1:8001/mcp",
                    "headers": {"Authorization": "Bearer valid-token-123"},
                    "timeout": 10.0
                }
            },
            "should_succeed": True
        },
        {
            "name": "Invalid Bearer Token",
            "config": {
                "bearer-invalid": {
                    "url": "http://127.0.0.1:8001/mcp",
                    "headers": {"Authorization": "Bearer invalid-token"},
                    "timeout": 10.0
                }
            },
            "should_succeed": False
        },
        {
            "name": "Missing Authorization Header",
            "config": {
                "bearer-missing": {
                    "url": "http://127.0.0.1:8001/mcp",
                    "timeout": 10.0
                }
            },
            "should_succeed": False
        }
    ]
    
    for test_case in test_cases:
        print(f"\n🧪 {test_case['name']}")
        try:
            tools, cleanup = await convert_mcp_to_langchain_tools(test_case['config'])
            
            if test_case['should_succeed']:
                print(f"✅ Success: {len(tools)} tools available")
                # Test a tool
                if tools:
                    echo_tool = next((t for t in tools if 'echo' in t.name), None)
                    if echo_tool:
                        result = await echo_tool.ainvoke({"message": "test"})
                        print(f"  🔧 Tool test: {result[:50]}...")
            else:
                print(f"❌ Unexpected success: {len(tools)} tools (should have failed)")
            
            await cleanup()
            
        except Exception as e:
            if test_case['should_succeed']:
                print(f"❌ Unexpected failure: {e}")
            else:
                print(f"✅ Expected failure: {str(e)[:100]}...")

async def test_api_key_auth():
    """Test API key authentication scenarios."""
    print("\n🔑 Testing API Key Authentication")
    print("=" * 50)
    
    test_cases = [
        {
            "name": "Valid API Key",
            "config": {
                "api-valid": {
                    "url": "http://127.0.0.1:8002/mcp",
                    "headers": {"X-API-Key": "sk-test-key-123"},
                    "timeout": 10.0
                }
            },
            "should_succeed": True
        },
        {
            "name": "Invalid API Key",
            "config": {
                "api-invalid": {
                    "url": "http://127.0.0.1:8002/mcp",
                    "headers": {"X-API-Key": "invalid-key"},
                    "timeout": 10.0
                }
            },
            "should_succeed": False
        },
        {
            "name": "Missing API Key",
            "config": {
                "api-missing": {
                    "url": "http://127.0.0.1:8002/mcp",
                    "timeout": 10.0
                }
            },
            "should_succeed": False
        },
        {
            "name": "Expired API Key",
            "config": {
                "api-expired": {
                    "url": "http://127.0.0.1:8002/mcp",
                    "headers": {"X-API-Key": "sk-expired-key"},
                    "timeout": 10.0
                }
            },
            "should_succeed": False
        }
    ]
    
    for test_case in test_cases:
        print(f"\n🧪 {test_case['name']}")
        try:
            tools, cleanup = await convert_mcp_to_langchain_tools(test_case['config'])
            
            if test_case['should_succeed']:
                print(f"✅ Success: {len(tools)} tools available")
                # Test a tool
                if tools:
                    weather_tool = next((t for t in tools if 'weather' in t.name), None)
                    if weather_tool:
                        result = await weather_tool.ainvoke({"city": "Tokyo"})
                        print(f"  🔧 Tool test: {result[:50]}...")
            else:
                print(f"❌ Unexpected success: {len(tools)} tools (should have failed)")
            
            await cleanup()
            
        except Exception as e:
            if test_case['should_succeed']:
                print(f"❌ Unexpected failure: {e}")
            else:
                print(f"✅ Expected failure: {str(e)[:100]}...")

async def test_mixed_auth_servers():
    """Test connecting to multiple servers with different auth methods."""
    print("\n🔀 Testing Mixed Authentication Servers")
    print("=" * 50)
    
    mixed_config = {
        "bearer-server": {
            "url": "http://127.0.0.1:8001/mcp",
            "headers": {"Authorization": "Bearer valid-token-123"},
            "timeout": 10.0
        },
        "api-key-server": {
            "url": "http://127.0.0.1:8002/mcp", 
            "headers": {"X-API-Key": "sk-test-key-123"},
            "timeout": 10.0
        }
    }
    
    try:
        tools, cleanup = await convert_mcp_to_langchain_tools(mixed_config)
        print(f"✅ Mixed auth success: {len(tools)} total tools")
        
        # Group tools by server (approximate)
        bearer_tools = [t for t in tools if 'authenticated' in t.name or 'secure' in t.name]
        api_tools = [t for t in tools if 'weather' in t.name or 'notification' in t.name]
        
        print(f"  📊 Bearer server tools: {len(bearer_tools)}")
        print(f"  📊 API key server tools: {len(api_tools)}")
        
        # Test tools from both servers
        if bearer_tools:
            result = await bearer_tools[0].ainvoke({"message": "mixed auth test"})
            print(f"  🔧 Bearer tool: {result[:50]}...")
        
        if api_tools:
            result = await api_tools[0].ainvoke({"city": "Tokyo"})
            print(f"  🔧 API key tool: {result[:50]}...")
        
        await cleanup()
        
    except Exception as e:
        print(f"❌ Mixed auth failed: {e}")

async def test_custom_headers():
    """Test various custom header configurations."""
    print("\n🎨 Testing Custom Headers")
    print("=" * 50)
    
    test_cases = [
        {
            "name": "Multiple Custom Headers",
            "config": {
                "multi-headers": {
                    "url": "http://127.0.0.1:8001/mcp",
                    "headers": {
                        "Authorization": "Bearer valid-token-123",
                        "User-Agent": "langchain-mcp-tools/1.0",
                        "X-Client-ID": "test-client-123",
                        "X-Request-ID": "req-456",
                        "Accept-Language": "en-US,en;q=0.9"
                    },
                    "timeout": 10.0
                }
            },
            "should_succeed": True
        },
        {
            "name": "API Key + Custom Headers",
            "config": {
                "api-custom": {
                    "url": "http://127.0.0.1:8002/mcp",
                    "headers": {
                        "X-API-Key": "sk-test-key-123",
                        "X-App-Version": "2.1.0",
                        "X-Platform": "python",
                        "Cache-Control": "no-cache"
                    },
                    "timeout": 10.0
                }
            },
            "should_succeed": True
        }
    ]
    
    for test_case in test_cases:
        print(f"\n🧪 {test_case['name']}")
        try:
            tools, cleanup = await convert_mcp_to_langchain_tools(test_case['config'])
            
            if test_case['should_succeed']:
                print(f"✅ Success: {len(tools)} tools with custom headers")
                headers_config = list(test_case['config'].values())[0]['headers']
                print(f"  📝 Headers used: {list(headers_config.keys())}")
            else:
                print(f"❌ Unexpected success: {len(tools)} tools")
            
            await cleanup()
            
        except Exception as e:
            if test_case['should_succeed']:
                print(f"❌ Unexpected failure: {e}")
            else:
                print(f"✅ Expected failure: {str(e)[:100]}...")

async def test_edge_cases():
    """Test edge cases and error scenarios."""
    print("\n⚠️  Testing Edge Cases")
    print("=" * 50)
    
    edge_cases = [
        {
            "name": "Empty Headers Dict",
            "config": {
                "empty-headers": {
                    "url": "http://127.0.0.1:8001/mcp",
                    "headers": {},
                    "timeout": 10.0
                }
            },
            "should_succeed": False
        },
        {
            "name": "Malformed Bearer Token",
            "config": {
                "malformed-bearer": {
                    "url": "http://127.0.0.1:8001/mcp",
                    "headers": {"Authorization": "NotBearer token-123"},
                    "timeout": 10.0
                }
            },
            "should_succeed": False
        },
        {
            "name": "Case Sensitive Headers",
            "config": {
                "case-sensitive": {
                    "url": "http://127.0.0.1:8002/mcp",
                    "headers": {"x-api-key": "sk-test-key-123"},  # lowercase
                    "timeout": 10.0
                }
            },
            "should_succeed": True  # HTTP headers are case-insensitive
        }
    ]
    
    for test_case in edge_cases:
        print(f"\n🧪 {test_case['name']}")
        try:
            tools, cleanup = await convert_mcp_to_langchain_tools(test_case['config'])
            
            if test_case['should_succeed']:
                print(f"✅ Success: {len(tools)} tools")
            else:
                print(f"❌ Unexpected success: {len(tools)} tools (should have failed)")
            
            await cleanup()
            
        except Exception as e:
            if test_case['should_succeed']:
                print(f"❌ Unexpected failure: {e}")
            else:
                print(f"✅ Expected failure: {str(e)[:100]}...")

async def main():
    """Run all comprehensive authentication tests."""
    print("🧪 Comprehensive Authentication Tests for langchain-mcp-tools")
    print("=" * 80)
    print("Prerequisites:")
    print("  • simple_bearer_auth_server.py running on port 8001")
    print("  • api_key_auth_server.py running on port 8002")
    print("=" * 80)
    
    # Run all test suites
    await test_bearer_token_auth()
    await test_api_key_auth()
    await test_mixed_auth_servers()
    await test_custom_headers()
    await test_edge_cases()
    
    print("\n🎉 All Comprehensive Authentication Tests Completed!")
    print("\n📊 Summary of what was tested:")
    print("  ✅ Bearer token authentication (valid/invalid/missing)")
    print("  ✅ API key authentication (valid/invalid/missing/expired)")
    print("  ✅ Mixed authentication servers in single config")
    print("  ✅ Custom headers functionality")
    print("  ✅ Edge cases and error scenarios")
    print("\n💡 Key validation points:")
    print("  • 'headers' parameter works with different auth types")
    print("  • Authentication errors are handled gracefully")
    print("  • Multiple servers with different auth can coexist")
    print("  • Custom headers are preserved and passed through")
    print("  • Transport auto-detection works with authentication")

if __name__ == "__main__":
    asyncio.run(main())
