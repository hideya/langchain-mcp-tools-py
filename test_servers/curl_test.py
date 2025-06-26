#!/usr/bin/env python3
"""
Manual curl test script for MCP Streamable HTTP servers.

This script provides easy curl commands to manually test your MCP servers.
Useful for debugging transport detection and message format issues.

Usage:
    # Start a test server first:
    python simple_stateless_server.py
    
    # Then run the curl tests:
    python curl_test.py
"""

import json
import subprocess
import sys

BASE_URL = "http://localhost:8000/mcp"

def run_curl(method, url, headers=None, data=None):
    """Run a curl command and return the result."""
    cmd = ["curl", "-X", method, url]
    
    if headers:
        for key, value in headers.items():
            cmd.extend(["-H", f"{key}: {value}"])
    
    if data:
        cmd.extend(["-d", json.dumps(data)])
    
    cmd.extend(["-v", "--no-progress-meter"])  # Verbose output, no progress meter
    
    print(f"🔍 Running: {' '.join(cmd)}")
    print("-" * 60)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        print("📤 STDOUT:")
        print(result.stdout)
        if result.stderr:
            print("📥 STDERR:")
            print(result.stderr)
        print("🏁 Return code:", result.returncode)
        return result
    except subprocess.TimeoutExpired:
        print("⏰ Request timed out")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_initialize():
    """Test the initialize request (transport detection)."""
    print("🚀 Testing Initialize Request (Transport Detection)")
    print("=" * 60)
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream"
    }
    
    data = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "curl-test",
                "version": "1.0.0"
            }
        }
    }
    
    result = run_curl("POST", BASE_URL, headers, data)
    
    if result and result.returncode == 0:
        print("✅ Initialize request successful")
        try:
            response = json.loads(result.stdout)
            print("📋 Response:")
            print(json.dumps(response, indent=2))
        except json.JSONDecodeError:
            print("⚠️  Response is not valid JSON")
    else:
        print("❌ Initialize request failed")
    
    return result

def test_list_tools():
    """Test listing available tools."""
    print("\n🛠️  Testing List Tools Request")
    print("=" * 60)
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    data = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    }
    
    result = run_curl("POST", BASE_URL, headers, data)
    
    if result and result.returncode == 0:
        print("✅ List tools request successful")
        try:
            response = json.loads(result.stdout)
            tools = response.get("result", {}).get("tools", [])
            print(f"📋 Found {len(tools)} tools:")
            for tool in tools:
                print(f"  • {tool.get('name', 'N/A')}: {tool.get('description', 'N/A')}")
        except json.JSONDecodeError:
            print("⚠️  Response is not valid JSON")
    else:
        print("❌ List tools request failed")
    
    return result

def test_call_tool():
    """Test calling a specific tool."""
    print("\n⚡ Testing Call Tool Request")
    print("=" * 60)
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    data = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "add",
            "arguments": {
                "a": 5,
                "b": 3
            }
        }
    }
    
    result = run_curl("POST", BASE_URL, headers, data)
    
    if result and result.returncode == 0:
        print("✅ Call tool request successful")
        try:
            response = json.loads(result.stdout)
            print("📋 Response:")
            print(json.dumps(response, indent=2))
        except json.JSONDecodeError:
            print("⚠️  Response is not valid JSON")
    else:
        print("❌ Call tool request failed")
    
    return result

def test_sse_fallback():
    """Test SSE fallback behavior (should not be needed with these servers)."""
    print("\n📡 Testing SSE Fallback (GET request)")
    print("=" * 60)
    
    headers = {
        "Accept": "text/event-stream"
    }
    
    result = run_curl("GET", BASE_URL, headers)
    
    if result:
        if result.returncode == 0:
            print("✅ SSE GET request successful (unexpected for stateless server)")
        elif "405" in result.stderr or "Method Not Allowed" in result.stderr:
            print("✅ SSE GET request properly rejected (expected for stateless server)")
        else:
            print("❓ SSE GET request failed with unexpected error")
    
    return result

def main():
    """Run all curl tests."""
    print("🧪 Manual Curl Tests for MCP Streamable HTTP Server")
    print("=" * 70)
    print(f"🎯 Target URL: {BASE_URL}")
    print("📋 Make sure your test server is running first!")
    print("=" * 70)
    
    # Test sequence
    tests = [
        ("Initialize", test_initialize),
        ("List Tools", test_list_tools), 
        ("Call Tool", test_call_tool),
        ("SSE Fallback", test_sse_fallback)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = result.returncode == 0 if result else False
        except KeyboardInterrupt:
            print(f"\n⏹️  Test interrupted by user")
            break
        except Exception as e:
            print(f"\n❌ Test '{test_name}' failed with error: {e}")
            results[test_name] = False
    
    # Summary
    print("\n📊 Test Results Summary")
    print("=" * 40)
    
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status} {test_name}")
    
    passed = sum(1 for success in results.values() if success)
    total = len(results)
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Your server is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the server logs and responses above.")
    
    print("\n💡 Tips for debugging:")
    print("  • Check server logs for error messages")
    print("  • Verify the server is running on the expected port")
    print("  • Ensure Content-Type and Accept headers are correct")
    print("  • Validate JSON-RPC message format")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
