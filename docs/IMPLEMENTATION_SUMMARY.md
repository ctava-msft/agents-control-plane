# Central Memory + Foundry IQ Implementation Summary

## Overview

This implementation adds enterprise-grade memory and orchestration capabilities to the AI Agents Control Plane, following the architecture outlined in the Azure Cross-Cloud AI Agents Control Plane Solution Architecture PDF.

## What Was Implemented

### 1. Infrastructure Components (Bicep Modules)

#### Cosmos DB (`infra/core/database/cosmosdb.bicep`)
- **Purpose**: Long-term memory storage for agent conversations and tool traces
- **Features**:
  - Serverless configuration for cost optimization
  - Two containers: `threads` (conversations) and `tool-traces` (execution history)
  - Partition keys optimized for agent-based queries
  - Automatic indexing for efficient queries

#### Azure AI Search (`infra/core/search/ai-search.bicep`)
- **Purpose**: Knowledge base indexing and Foundry IQ agentic search
- **Features**:
  - Basic tier for cost-effective deployment
  - Entra ID authentication (local auth disabled)
  - System-assigned managed identity for secure access
  - Ready for semantic search capabilities

#### Azure AI Foundry Agent Service (`infra/core/ai/foundry-agent-service.bicep`)
- **Purpose**: Multi-agent orchestration and tool registry
- **Components**:
  - AI Hub: Central governance for AI projects
  - AI Project: Workspace for agent development and deployment
  - Integration with Key Vault, Storage, App Insights, and ACR
  - System-assigned managed identities for secure access

#### Key Vault (`infra/core/security/keyvault.bicep`)
- **Purpose**: Secure secrets storage for AI Hub
- **Features**:
  - RBAC authorization enabled
  - Soft delete for 7-day retention
  - Standard tier for general use

### 2. MCP Server Integration

#### Foundry IQ Client (`src/foundry_iq_client.py`)
- **Capabilities**:
  - Azure AI Search integration for knowledge base queries
  - Automatic index creation with proper schema
  - Full-text search with category filtering
  - Document indexing with metadata support
  - OpenTelemetry tracing for all operations
  - FabricIQ alignment notes for Microsoft Fabric integration

#### Cosmos Memory Client (`src/cosmos_memory_client.py`)
- **Capabilities**:
  - Store and retrieve conversation threads by agent and thread ID
  - Store tool execution traces for audit and debugging
  - Query recent tool traces for analysis
  - OpenTelemetry tracing for all operations
  - Efficient partition-based queries

#### MCP Server Updates (`src/mcp_server.py`)
- **New Features**:
  - `foundry_iq_search` tool for knowledge base queries
  - OpenTelemetry integration with Azure Monitor
  - Automatic trace storage in Cosmos DB
  - Proper logging initialization order

### 3. Tool Registry & Orchestration

#### Tool Registry Client (`src/tool_registry.py`)
- **Capabilities**:
  - MCP tool registration (stub implementation)
  - OpenAPI tool registration (stub implementation)
  - Batch tool synchronization
  - Comprehensive logging for manual registration

**Note**: Tool registration is currently a stub implementation because the Azure AI Projects SDK is in beta. Tool definitions are logged for manual registration until the SDK reaches GA.

### 4. Documentation

#### Tool Registry Guide (`docs/TOOL_REGISTRY.md`)
- Architecture diagrams
- Tool catalog sync flow
- Configuration examples
- Access control setup
- Monitoring and troubleshooting

#### Azure AI Search Queries (`docs/AZURE_SEARCH_QUERIES.md`)
- Index schema documentation
- Sample queries for common use cases
- OData filter syntax examples
- Performance optimization tips
- Access control with ACLs

#### Updated README
- New architecture diagram with memory and orchestration
- Central Memory usage examples
- Foundry IQ search examples
- Multi-agent orchestration setup
- Environment variable configuration

### 5. Testing

#### Integration Tests (`tests/test_foundry_integration.py`)
- Foundry IQ client initialization and search
- Cosmos memory thread storage and retrieval
- Tool trace storage and queries
- Tool registry operations
- MCP tool integration tests

## Environment Variables

The implementation requires these new environment variables:

```bash
# Cosmos DB Configuration
COSMOS_DB_ENDPOINT=https://your-cosmos.documents.azure.com:443/
COSMOS_DB_DATABASE_NAME=agents-memory
COSMOS_DB_THREADS_CONTAINER=threads
COSMOS_DB_TRACES_CONTAINER=tool-traces

# Azure AI Search Configuration
AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
AZURE_SEARCH_INDEX_NAME=agent-knowledge-base

# Azure AI Foundry Agent Service
AI_PROJECT_ENDPOINT=https://your-project.api.azureml.ms
AI_PROJECT_NAME=your-project-name
MCP_ENDPOINT_URL=https://your-apim.azure-api.net/mcp

# Application Insights (already exists)
APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=...
```

## Deployment

### Step 1: Deploy Infrastructure

```bash
# Deploy all resources including new components
azd up
```

This creates:
- Cosmos DB account with database and containers
- Azure AI Search service with managed identity
- Azure AI Foundry Hub and Project
- Key Vault for secrets
- All necessary RBAC role assignments

### Step 2: Update MCP Server

```bash
# Set new environment variables
export COSMOS_DB_ENDPOINT=$(azd env get-values | grep COSMOS_DB_ENDPOINT | cut -d'=' -f2 | tr -d '"')
export AZURE_SEARCH_ENDPOINT=$(azd env get-values | grep AZURE_SEARCH_ENDPOINT | cut -d'=' -f2 | tr -d '"')

# Build and deploy MCP server
./scripts/build-and-push.sh
envsubst < k8s/mcp-server-deployment.yaml | kubectl apply -f -
```

### Step 3: Initialize Knowledge Base (Optional)

```python
from src.foundry_iq_client import create_foundry_iq_client

# Create and initialize index
client = create_foundry_iq_client()
client.ensure_index_exists()

# Index initial documents
await client.index_document(
    doc_id="doc-001",
    content="Your documentation content...",
    title="Getting Started",
    category="documentation"
)
```

### Step 4: Register Tools (Future)

```bash
# Currently logs tool definitions for manual registration
python -m tool_registry sync \
  --mcp-endpoint "$(azd env get-values | grep MCP_ENDPOINT_URL | cut -d'=' -f2 | tr -d '"')" \
  --ai-project-endpoint "$(azd env get-values | grep AI_PROJECT_ENDPOINT | cut -d'=' -f2 | tr -d '"')"
```

## Usage Examples

### Search Knowledge Base

Via MCP tool:
```json
{
  "tool": "foundry_iq_search",
  "arguments": {
    "query": "How do I configure authentication?",
    "top": 5,
    "category": "security"
  }
}
```

Via Python:
```python
from src.foundry_iq_client import create_foundry_iq_client

client = create_foundry_iq_client()
results = await client.search_knowledge_base(
    query="deployment best practices",
    top=10
)
```

### Access Conversation History

```python
from src.cosmos_memory_client import create_cosmos_memory_client

memory = create_cosmos_memory_client()
history = await memory.get_thread_history(
    agent_id="my-agent",
    thread_id="conversation-123"
)
```

### Query Tool Traces

```python
traces = await memory.query_tool_traces(
    tool_name="foundry_iq_search",
    limit=20
)
```

## Monitoring

All operations are traced in Application Insights with custom spans:

- `foundry_iq.search` - Knowledge base searches
- `foundry_iq.index_document` - Document indexing
- `cosmos.store_thread_message` - Thread message storage
- `cosmos.get_thread_history` - Thread retrieval
- `cosmos.store_tool_trace` - Tool trace storage
- `mcp.foundry_iq_search` - MCP tool execution

View traces in Azure Portal → Application Insights → Transaction search.

## Security

### Access Control
- **Cosmos DB**: Managed identity with built-in Data Contributor role
- **Azure AI Search**: Managed identity with Search Index Data Contributor role
- **Key Vault**: RBAC authorization for secret access
- **Storage**: Existing blob storage access maintained

### Data Protection
- All data encrypted at rest (Azure default)
- TLS for all network communication
- Private endpoints supported (if vnetEnabled=true)
- ACL support in Azure AI Search

## Cost Optimization

- **Cosmos DB**: Serverless mode (pay per operation)
- **Azure AI Search**: Basic tier (can scale up if needed)
- **AI Foundry**: Basic tier (no compute charges until agents run)
- **Key Vault**: Standard tier (no premium HSM)

Estimated monthly cost (light usage):
- Cosmos DB Serverless: ~$5-20
- Azure AI Search Basic: ~$75
- AI Foundry Hub+Project: ~$0-10
- Key Vault: ~$1

## Known Limitations

1. **Tool Registration**: Currently a stub implementation. Requires GA Azure AI Projects SDK for actual registration.

2. **FabricIQ Integration**: Fabric data source alignment must be configured through Azure AI Foundry portal (not IaC).

3. **Vector Search**: Not enabled by default. Can be added to search index if needed for semantic search.

4. **Production Scale**: Consider:
   - Cosmos DB provisioned throughput for high-volume scenarios
   - Azure AI Search Standard tier for larger indexes
   - Redis for MCP session storage (currently in-memory)

## Future Enhancements

1. Enable tool registration once Azure AI Projects SDK is GA
2. Add vector embeddings for semantic search
3. Implement FabricIQ data source connectors
4. Add Redis for distributed session storage
5. Create UI for knowledge base management
6. Add more MCP tools for agent capabilities

## Troubleshooting

### Cosmos DB Connection Issues
- Verify managed identity has Data Contributor role
- Check network connectivity to Cosmos endpoint
- Ensure containers are created (automatic on first deployment)

### Search Not Working
- Run `client.ensure_index_exists()` to create index
- Verify managed identity has Search Index Data Contributor role
- Check if documents are indexed

### Tool Registration Not Working
- This is expected - implementation is currently a stub
- Check logs for tool definitions
- Register tools manually in Azure AI Foundry portal

## Support

For issues or questions:
1. Check logs in Application Insights
2. Review documentation in `docs/` folder
3. See Azure service health status
4. Open GitHub issue with detailed logs

## References

- [Azure AI Foundry Documentation](https://learn.microsoft.com/azure/ai-studio/)
- [Azure Cosmos DB RBAC](https://learn.microsoft.com/azure/cosmos-db/how-to-setup-rbac)
- [Azure AI Search](https://learn.microsoft.com/azure/search/)
- [MCP Protocol](https://modelcontextprotocol.io/)
