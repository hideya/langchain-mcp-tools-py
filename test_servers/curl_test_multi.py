#!/usr/bin/env python3
"""
Multi-server curl test script for the FastAPI multi-server setup.

This script tests all three endpoints from multi_server_fastapi.py.

Usage:
    # Start the multi-server first:
    python multi_server_fastapi.py
    
    # Then run these curl tests:
    python curl_test_multi.py
"""

import json
import subprocess
import sys

ENDPOINTS = {
    "echo": "http://localhost:8000/echo/mcp",
    "math": "http://localhost:8000/math/mcp", 
    "utils": "http://localhost:8000/utils/mcp"
}

def run_curl(method, url, headers=None, data=None):
    """Run a curl command and return the result."""
    cmd = ["curl", "-X", method, url]
    
    if headers:
        for key, value in headers.items():
            cmd.extend(["-H", f"{key}: {value}"])
    
    if data:
        cmd.extend(["-d", json.dumps(data)])
    
    cmd.extend(["-v", "--no-progress-meter"])
    
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

def test_server(server_name, base_url):
    """Test a specific server endpoint."""
    print(f"\n🧪 Testing {server_name.upper()} Server: {base_url}")
    print("=" * 70)
    
    results = {}
    
    # Test 1: Initialize
    print(f"🚀 Testing Initialize Request for {server_name}")
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
            "clientInfo": {"name": f"curl-test-{server_name}", "version": "1.0.0"}
        }
    }
    result = run_curl("POST", base_url, headers, data)
    results["initialize"] = result.returncode == 0 if result else False
    
    # Test 2: List Tools
    print(f"\n🛠️  Testing List Tools for {server_name}")
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    data = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    result = run_curl("POST", base_url, headers, data)
    results["list_tools"] = result.returncode == 0 if result else False
    
    if result and result.returncode == 0:
        try:
            response = json.loads(result.stdout)
            tools = response.get("result", {}).get("tools", [])
            print(f"📋 Found {len(tools)} tools:")
            for tool in tools:
                print(f"  • {tool.get('name', 'N/A')}: {tool.get('description', 'N/A')}")
        except json.JSONDecodeError:
            pass
    
    # Test 3: Call a tool (server-specific)
    tool_tests = {
        "echo": {"name": "echo", "arguments": {"message": "test"}},
        "math": {"name": "add", "arguments": {"a": 5, "b": 3}},
        "utils": {"name": "generate_uuid", "arguments": {}}
    }
    
    if server_name in tool_tests:
        print(f"\n⚡ Testing Tool Call for {server_name}")
        test_tool = tool_tests[server_name]
        data = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": test_tool
        }
        result = run_curl("POST", base_url, headers, data)
        results["call_tool"] = result.returncode == 0 if result else False
        
        if result and result.returncode == 0:
            try:
                response = json.loads(result.stdout)
                print("📋 Tool Response:")
                print(json.dumps(response, indent=2))
            except json.JSONDecodeError:
                pass
    
    return results

def main():
    """Test all servers in the multi-server setup."""
    print("🧪 Multi-Server Curl Tests for FastAPI MCP Setup")
    print("=" * 70)
    print("🎯 Testing multiple endpoints:")
    for name, url in ENDPOINTS.items():
        print(f"  • {name}: {url}")
    print("📋 Make sure multi_server_fastapi.py is running!")
    print("=" * 70)
    
    all_results = {}
    
    # Test each server
    for server_name, base_url in ENDPOINTS.items():
        try:
            results = test_server(server_name, base_url)
            all_results[server_name] = results
        except KeyboardInterrupt:
            print(f"\n⏹️  Testing interrupted by user")
            break
        except Exception as e:
            print(f"\n❌ Error testing {server_name}: {e}")
            all_results[server_name] = {"error": True}
    
    # Summary
    print("\n📊 Multi-Server Test Results Summary")
    print("=" * 50)
    
    for server_name, results in all_results.items():
        if "error" in results:
            print(f"❌ {server_name.upper()}: ERROR")
            continue
            
        print(f"\n🎯 {server_name.upper()} Server:")
        for test_name, success in results.items():
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"  {status} {test_name}")
    
    # Overall stats
    total_tests = sum(len(r) for r in all_results.values() if "error" not in r)
    passed_tests = sum(sum(1 for s in r.values() if s) for r in all_results.values() if "error" not in r)
    
    print(f"\n🎯 Overall: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All multi-server tests passed!")
    else:
        print("⚠️  Some tests failed. Check the server logs and responses above.")
    
    print("\n💡 Note: This tests the multi-server FastAPI setup.")
    print("   For single-server testing, use curl_test.py with simple_stateless_server.py")
    print("\n💡 Note: You may see '307 Temporary Redirect' in the server logs.")
    print("   This is normal FastAPI behavior for ensuring consistent URL formatting.")
    print("   FastAPI automatically redirects /path to /path/ - the requests still succeed!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
