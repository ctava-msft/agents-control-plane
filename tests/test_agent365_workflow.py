#!/usr/bin/env python3
"""
Test Agent365 Approval Workflow
This script tests the Agent365 human-in-the-loop approval tools
"""

import os
import sys
import json
import requests
import re
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

def extract_approval_id(text: str) -> str:
    """Extract approval ID from response text"""
    match = re.search(r'ID: ([0-9a-f\-]+)', text)
    if match:
        return match.group(1)
    return None

def test_request_approval():
    """Test requesting human approval"""
    print("Test 1: Request Approval")
    print("-" * 50)
    
    try:
        result = call_mcp_tool("request_approval", {
            "action": "Delete test data from production database",
            "context": "Cleanup after integration tests. Affects 100 records.",
            "requester": "test-automation-agent"
        })
        
        if result.get("result", {}).get("isError"):
            print(f"❌ Failed: {result}")
            return False, None
        
        response_text = result['result']['content'][0]['text']
        approval_id = extract_approval_id(response_text)
        
        if approval_id:
            print("✅ Approval request created successfully")
            print(f"   Approval ID: {approval_id}")
            print(f"   Response: {response_text[:200]}")
            return True, approval_id
        else:
            print("❌ Could not extract approval ID from response")
            return False, None
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return False, None

def test_check_approval_status(approval_id: str):
    """Test checking approval status"""
    print("\nTest 2: Check Approval Status")
    print("-" * 50)
    
    if not approval_id:
        print("⚠️  Skipping (no approval ID)")
        return False
    
    try:
        result = call_mcp_tool("check_approval_status", {
            "approval_id": approval_id
        })
        
        if result.get("result", {}).get("isError"):
            print(f"❌ Failed: {result}")
            return False
        
        response_text = result['result']['content'][0]['text']
        print("✅ Approval status retrieved")
        print(f"   Response: {response_text[:200]}")
        
        # Check if it contains the approval ID
        if approval_id in response_text:
            print("✅ Response contains correct approval ID")
            return True
        else:
            print("❌ Response does not contain approval ID")
            return False
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_list_tools():
    """Test that Agent365 tools are available"""
    print("\nTest 3: Verify Agent365 Tools are Available")
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
        
        required_tools = ["request_approval", "check_approval_status"]
        found_tools = [name for name in required_tools if name in tool_names]
        
        if len(found_tools) == len(required_tools):
            print(f"✅ All Agent365 tools available: {found_tools}")
            
            # Print tool descriptions
            for tool in tools:
                if tool["name"] in required_tools:
                    print(f"\n   {tool['name']}: {tool['description']}")
            
            return True
        else:
            print(f"❌ Missing tools. Found: {found_tools}, Required: {required_tools}")
            return False
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_multiple_approvals():
    """Test creating multiple approval requests"""
    print("\nTest 4: Multiple Approval Requests")
    print("-" * 50)
    
    actions = [
        "Update production configuration",
        "Deploy new version to staging",
        "Modify user permissions"
    ]
    
    approval_ids = []
    
    try:
        for action in actions:
            result = call_mcp_tool("request_approval", {
                "action": action,
                "context": "Test scenario",
                "requester": "test-agent"
            })
            
            if not result.get("result", {}).get("isError"):
                response_text = result['result']['content'][0]['text']
                approval_id = extract_approval_id(response_text)
                if approval_id:
                    approval_ids.append(approval_id)
        
        if len(approval_ids) == len(actions):
            print(f"✅ Created {len(approval_ids)} approval requests")
            for i, aid in enumerate(approval_ids, 1):
                print(f"   {i}. {aid}")
            return True
        else:
            print(f"❌ Only created {len(approval_ids)}/{len(actions)} approvals")
            return False
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 50)
    print("Agent365 Approval Workflow Tests")
    print("=" * 50)
    print()
    
    results = []
    
    # Test 1: List tools
    results.append(("List Tools", test_list_tools()))
    
    # Test 2: Request approval
    success, approval_id = test_request_approval()
    results.append(("Request Approval", success))
    
    # Test 3: Check status
    results.append(("Check Status", test_check_approval_status(approval_id)))
    
    # Test 4: Multiple approvals
    results.append(("Multiple Approvals", test_multiple_approvals()))
    
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
    
    print("\n📝 Note: This tests the approval workflow infrastructure.")
    print("   In production, approvals would be processed by:")
    print("   - Power Automate flows")
    print("   - Teams adaptive cards")
    print("   - Custom web dashboards")
    print("   - Azure Logic Apps")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print(f"\n❌ {total - passed} test(s) failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
