#!/usr/bin/env python3
"""
Test Key Vault Integration
This script tests the Key Vault MCP tools
"""

import os
import sys
import json
import requests
from typing import Dict, Any

# Configuration
APIM_BASE_URL = os.getenv("SERVICE_API_ENDPOINT", "").replace("/mcp/sse", "")
MCP_TOKEN = os.getenv("MCP_ACCESS_TOKEN", "")

def call_mcp_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Call an MCP tool via APIM"""
    if not APIM_BASE_URL or not MCP_TOKEN:
        print("Error: SERVICE_API_ENDPOINT and MCP_ACCESS_TOKEN must be set")
        sys.exit(1)
    
    url = f"{APIM_BASE_URL}/mcp/message"
    headers = {
        "Authorization": f"Bearer {MCP_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        },
        "id": 1
    }
    
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()

def test_set_secret():
    """Test setting a secret in Key Vault"""
    print("Test 1: Set Secret in Key Vault")
    print("-" * 50)
    
    try:
        result = call_mcp_tool("set_secret", {
            "secret_name": "test-api-key",
            "secret_value": "sk-test-12345-abcde"
        })
        
        if result.get("result", {}).get("isError"):
            print(f"❌ Failed: {result}")
            return False
        
        print("✅ Secret stored successfully")
        print(f"   Response: {result['result']['content'][0]['text']}")
        return True
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_get_secret():
    """Test retrieving a secret from Key Vault"""
    print("\nTest 2: Get Secret from Key Vault")
    print("-" * 50)
    
    try:
        result = call_mcp_tool("get_secret", {
            "secret_name": "test-api-key"
        })
        
        if result.get("result", {}).get("isError"):
            print(f"❌ Failed: {result}")
            return False
        
        secret_value = result['result']['content'][0]['text']
        print("✅ Secret retrieved successfully")
        print(f"   Value: {secret_value}")
        
        # Verify it matches what we set
        if secret_value == "sk-test-12345-abcde":
            print("✅ Secret value matches expected value")
            return True
        else:
            print(f"❌ Secret value mismatch")
            return False
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_get_nonexistent_secret():
    """Test error handling for non-existent secret"""
    print("\nTest 3: Get Non-Existent Secret (Error Handling)")
    print("-" * 50)
    
    try:
        result = call_mcp_tool("get_secret", {
            "secret_name": "nonexistent-secret-xyz"
        })
        
        if result.get("result", {}).get("isError"):
            print("✅ Correctly returned error for non-existent secret")
            print(f"   Error: {result['result']['content'][0]['text']}")
            return True
        else:
            print("❌ Should have returned an error")
            return False
    
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_list_tools():
    """Test that Key Vault tools are available"""
    print("\nTest 4: Verify Key Vault Tools are Available")
    print("-" * 50)
    
    try:
        url = f"{APIM_BASE_URL}/mcp/message"
        headers = {
            "Authorization": f"Bearer {MCP_TOKEN}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 1
        }
        
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        
        tools = result.get("result", {}).get("tools", [])
        tool_names = [tool["name"] for tool in tools]
        
        required_tools = ["get_secret", "set_secret"]
        found_tools = [name for name in required_tools if name in tool_names]
        
        if len(found_tools) == len(required_tools):
            print(f"✅ All Key Vault tools available: {found_tools}")
            return True
        else:
            print(f"❌ Missing tools. Found: {found_tools}, Required: {required_tools}")
            return False
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 50)
    print("Key Vault Integration Tests")
    print("=" * 50)
    print()
    
    results = []
    
    # Test 1: List tools
    results.append(("List Tools", test_list_tools()))
    
    # Test 2: Set secret
    results.append(("Set Secret", test_set_secret()))
    
    # Test 3: Get secret
    results.append(("Get Secret", test_get_secret()))
    
    # Test 4: Error handling
    results.append(("Error Handling", test_get_nonexistent_secret()))
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print()
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 50)
    
    if passed == total:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print(f"\n❌ {total - passed} test(s) failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
