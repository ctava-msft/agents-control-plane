# Tool Registry and Catalog Sync

This document describes the tool registration and catalog synchronization flow for the Azure AI Foundry Agent Service integration.

## Overview

The tool registry system enables:
- **MCP Tool Registration**: Sync MCP tools from the MCP server to Azure AI Foundry Agent Service
- **OpenAPI Tool Registration**: Register external APIs as tools via OpenAPI specifications
- **Centralized Tool Catalog**: Unified tool catalog across multiple agents
- **Multi-Agent Orchestration**: Enable agent-to-agent communication and tool sharing

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Agent Applications                          │
│  (Claude Desktop, Custom Agents, Multi-Agent Systems)          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              Azure AI Foundry Agent Service                     │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                   Tool Catalog                            │ │
│  │  • MCP Tools (hello_mcp, get_snippet, foundry_iq_search) │ │
│  │  • OpenAPI Tools (external APIs)                         │ │
│  │  • Function Tools (custom implementations)               │ │
│  └───────────────────────────────────────────────────────────┘ │
└────────────────────────┬────────────────────────────────────────┘
                         │
         ┌───────────────┴───────────────┐
         │                               │
         ▼                               ▼
┌─────────────────┐            ┌─────────────────┐
│   MCP Server    │            │  OpenAPI APIs   │
│  (APIM + AKS)   │            │  (External)     │
└─────────────────┘            └─────────────────┘
```

## Tool Catalog Sync Flow

### 1. MCP Tool Registration

The MCP server exposes tools that can be registered with the Foundry Agent Service:

```python
from tool_registry import sync_tools_from_mcp_server

# Define MCP tools
mcp_tools = [
    {
        "name": "hello_mcp",
        "description": "Hello world MCP tool",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "foundry_iq_search",
        "description": "Search knowledge base using Foundry IQ",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "top": {"type": "integer", "description": "Number of results"}
            },
            "required": ["query"]
        }
    }
]

# Sync to Foundry Agent Service
mcp_endpoint = "https://your-apim.azure-api.net/mcp"
sync_tools_from_mcp_server(mcp_endpoint, mcp_tools)
```

### 2. OpenAPI Tool Registration

External APIs can be registered using OpenAPI specifications:

```python
from tool_registry import create_tool_registry_client

registry = create_tool_registry_client()

# Register an OpenAPI tool
registry.register_openapi_tool(
    tool_name="weather_api",
    openapi_spec_url="https://api.example.com/openapi.json",
    operation_id="getCurrentWeather",
    description="Get current weather for a location"
)
```

### 3. Automatic Sync on Deployment

The tool sync can be automated during deployment:

```bash
# After deploying the MCP server
python -m tool_registry sync \
  --mcp-endpoint "https://your-apim.azure-api.net/mcp" \
  --ai-project-endpoint "https://your-ai-project.api.azureml.ms"
```

## Configuration

Set the following environment variables:

```bash
# Azure AI Foundry Agent Service
export AI_PROJECT_ENDPOINT="https://your-ai-project.api.azureml.ms"
export AI_PROJECT_NAME="your-project-name"

# MCP Server endpoint (for tool registration)
export MCP_ENDPOINT_URL="https://your-apim.azure-api.net/mcp"
```

## Tool Execution Flow

1. **Agent Request**: Agent calls a tool through Foundry Agent Service
2. **Tool Lookup**: Agent Service looks up tool in catalog
3. **Routing**: Request is routed to appropriate endpoint (MCP or OpenAPI)
4. **Execution**: Tool is executed on the backend service
5. **Response**: Result is returned through Agent Service to agent
6. **Tracing**: Execution trace is stored in Cosmos DB

## Tool Schema Format

### MCP Tool Schema

```json
{
  "type": "function",
  "name": "tool_name",
  "description": "Tool description",
  "parameters": {
    "type": "object",
    "properties": {
      "param1": {
        "type": "string",
        "description": "Parameter description"
      }
    },
    "required": ["param1"]
  },
  "endpoint": {
    "type": "mcp",
    "url": "https://your-mcp-server.com/mcp",
    "method": "tools/call"
  }
}
```

### OpenAPI Tool Schema

```json
{
  "type": "openapi",
  "name": "tool_name",
  "description": "Tool description",
  "spec_url": "https://api.example.com/openapi.json",
  "operation_id": "operationId"
}
```

## Access Control

Tools registered in the catalog inherit ACLs from Azure AI Foundry:

- **User-level ACLs**: Control which users can invoke tools
- **Agent-level ACLs**: Control which agents can access tools
- **Resource-level ACLs**: Control access to underlying resources (Storage, Search, etc.)

### Configure ACLs in Azure Portal

1. Navigate to Azure AI Foundry Project
2. Go to "Tool Catalog" section
3. Select a tool and configure access policies
4. Assign roles: Owner, Contributor, Reader

## Sample Queries

### Azure AI Search Index Query

The Foundry IQ tool uses Azure AI Search. Sample queries:

```python
# Simple text search
results = await foundry_iq_client.search_knowledge_base(
    query="What are the deployment best practices?",
    top=5
)

# Filtered search
results = await foundry_iq_client.search_knowledge_base(
    query="authentication methods",
    top=10,
    filters="category eq 'security'"
)
```

### Search Index Structure

The default index schema includes:

- **id**: Unique document identifier
- **content**: Searchable text content
- **title**: Document title
- **category**: Filterable category (e.g., "security", "deployment", "api")
- **source**: Document source (e.g., "documentation", "code", "support")
- **timestamp**: Document creation/update time
- **metadata**: Additional JSON metadata

## Monitoring and Tracing

All tool executions are traced in Application Insights with Foundry IQ spans:

```
Tool Execution Span
├─ foundry_iq.search (if using search)
│  ├─ search.results_count: 5
│  └─ query: "deployment best practices"
├─ cosmos.store_tool_trace
│  ├─ tool_name: "foundry_iq_search"
│  └─ trace_id: "abc-123-def"
└─ mcp.foundry_iq_search
   ├─ search.results_count: 5
   └─ duration_ms: 145
```

### View Traces in Azure Portal

1. Navigate to Application Insights resource
2. Go to "Transaction search"
3. Filter by operation name: `mcp.foundry_iq_search`
4. View end-to-end transaction details

## FabricIQ Data Alignment

For integration with Microsoft Fabric data sources:

1. Navigate to Azure AI Foundry portal
2. Configure data connections to Fabric workspace
3. Map Fabric tables/views to search index
4. Enable automatic sync for real-time data updates

**Note**: FabricIQ alignment requires additional configuration in the Azure portal and is not covered by the infrastructure-as-code deployment.

## Troubleshooting

### Tool Registration Fails

Check that:
- AI_PROJECT_ENDPOINT is correctly set
- Managed identity has permissions on AI Project
- MCP endpoint is accessible from registration service

### Tools Not Visible to Agents

Verify:
- Tool sync completed successfully
- Agent has appropriate RBAC roles
- Tool catalog is refreshed (may take a few minutes)

### Search Returns No Results

Ensure:
- Azure AI Search index is created
- Documents are indexed (use `foundry_iq_client.index_document()`)
- Query syntax is valid
- Category filters match indexed documents

## Example: Complete Tool Registration

```python
#!/usr/bin/env python3
"""
Example: Register all MCP tools with Foundry Agent Service
"""

from tool_registry import create_tool_registry_client
import os

# MCP tools from mcp_server.py
MCP_TOOLS = [
    {
        "name": "hello_mcp",
        "description": "Hello world MCP tool",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "get_snippet",
        "description": "Retrieve a snippet from Azure Storage",
        "inputSchema": {
            "type": "object",
            "properties": {
                "snippetname": {"type": "string", "description": "Snippet name"}
            },
            "required": ["snippetname"]
        }
    },
    {
        "name": "foundry_iq_search",
        "description": "Search knowledge base using Foundry IQ",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "top": {"type": "integer", "description": "Number of results"}
            },
            "required": ["query"]
        }
    }
]

def main():
    mcp_endpoint = os.getenv("MCP_ENDPOINT_URL", "https://your-apim.azure-api.net/mcp")
    registry = create_tool_registry_client()
    
    if not registry:
        print("ERROR: Tool registry not configured")
        return 1
    
    # Register MCP tools
    print(f"Registering {len(MCP_TOOLS)} MCP tools...")
    results = registry.sync_mcp_tools(mcp_endpoint, MCP_TOOLS)
    
    # Register an example OpenAPI tool
    print("Registering OpenAPI tool example...")
    registry.register_openapi_tool(
        tool_name="example_api",
        openapi_spec_url="https://petstore3.swagger.io/api/v3/openapi.json",
        operation_id="getPetById",
        description="Example OpenAPI tool: Get pet by ID"
    )
    
    # Print results
    success_count = sum(1 for v in results.values() if v)
    print(f"\nRegistration complete: {success_count}/{len(results)} MCP tools successful")
    print("\nRegistered tools:")
    for tool_name, success in results.items():
        status = "✓" if success else "✗"
        print(f"  {status} {tool_name}")
    
    return 0 if success_count == len(results) else 1

if __name__ == "__main__":
    exit(main())
```

## See Also

- [Azure AI Foundry Documentation](https://learn.microsoft.com/azure/ai-studio/)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [Azure AI Search Documentation](https://learn.microsoft.com/azure/search/)
