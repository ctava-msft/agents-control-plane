# AI Agents with Azure Kubernetes Service, Kaito, and APIM

![AI Agent Architecture](mcp-client-authorization.gif)

Build powerful AI agents using **Azure Foundry models** deployed on Kubernetes with the **Model Context Protocol (MCP)**. This solution uses **Azure Kubernetes Service (AKS)**, **Kaito** for simplified LLM deployment, **Azure API Management (APIM)** as an intelligent AI Gateway, and **Azure AI Foundry Agent Service** for multi-agent orchestration.

## 🎯 What This Solution Provides

- **🤖 AI Agent Backend**: Deploy MCP servers that AI agents can interact with
- **📦 Azure Foundry Models**: Run enterprise-grade LLMs from Azure Foundry on Kubernetes
- **⚡ Kaito Framework**: Automated model deployment and scaling on AKS with GPU support
- **🔧 Custom Tools**: Extensible MCP tools for AI agents (snippet storage, custom integrations)
- **🛡️ Enterprise Security**: APIM gateway with OAuth authentication and authorization
- **📊 Production Ready**: Monitoring, logging, and auto-scaling built-in
- **🧠 Central Memory**: Cosmos DB for long-term agent memory and conversation threads
- **🔍 Foundry IQ**: Azure AI Search integration for agentic retrieval and reasoning
- **🎭 Multi-Agent Orchestration**: Azure AI Foundry Agent Service for coordinating multiple agents

## 🏗️ Architecture

```
AI Agent (Claude Desktop, etc.)
    ↓
Azure API Management (OAuth + Gateway)
    ↓
AKS Cluster
    ├── MCP Server (FastAPI)
    │   ├── Tools: hello_mcp, save_snippet, get_snippet, foundry_iq_search
    │   ├── Foundry IQ Client (Azure AI Search)
    │   └── Memory Client (Cosmos DB)
    └── Kaito Workspace
        └── Azure Foundry Model (Phi-3, etc.)
            └── GPU Node Pool (NC-series VMs)

Supporting Services:
├── Cosmos DB (Agent threads & tool traces)
├── Azure AI Search (Knowledge base & retrieval)
├── Azure AI Foundry Agent Service (Multi-agent orchestration)
└── Application Insights (Telemetry & tracing)
```

### Key Components

1. **AKS Cluster**: Kubernetes cluster with GPU-enabled node pools for model inference
2. **Kaito Operator**: Simplifies deploying and managing LLMs on Kubernetes
3. **MCP Server**: FastAPI application implementing Model Context Protocol
4. **Azure Foundry Models**: Enterprise LLMs (Phi-3, Llama, etc.) containerized and ready to deploy
5. **APIM**: Handles authentication, rate limiting, and API gateway functions
6. **Azure Storage**: Persistent storage for agent data (snippets, documents, etc.)
7. **Cosmos DB**: Long-term memory storage for agent conversations and tool execution traces
8. **Azure AI Search**: Knowledge base indexing and Foundry IQ agentic search
9. **Azure AI Foundry Agent Service**: Multi-agent orchestration and tool registry

### Available MCP Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `hello_mcp` | Simple test tool | None |
| `save_snippet` | Save text/code snippets to Azure Storage | `snippetname`, `snippet` |
| `get_snippet` | Retrieve saved snippets | `snippetname` |
| `foundry_iq_search` | Search knowledge base using Foundry IQ | `query`, `top` (optional), `category` (optional) |

## 🚀 Quick Start

### Prerequisites

- Azure subscription
- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) installed
- [Azure Developer CLI (azd)](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd) installed
- [Docker](https://docs.docker.com/get-docker/) installed
- [kubectl](https://kubernetes.io/docs/tasks/tools/) installed
- [Helm 3.x](https://helm.sh/docs/intro/install/) installed

### Step 1: Deploy Infrastructure

```bash
# Login to Azure
azd auth login
#az login --tenant 

# Deploy all Azure resources (AKS, ACR, APIM, Storage, etc.)
azd up
```

This command deploys:
- ✅ AKS cluster with GPU node pool
- ✅ Azure Container Registry
- ✅ Azure API Management
- ✅ Azure Storage account
- ✅ Managed identities and RBAC
- ✅ Application Insights monitoring

**⏱️ Deployment time**: ~15-20 minutes

### Step 2: Connect to AKS

```bash
# Get cluster credentials
export AKS_CLUSTER_NAME=$(azd env get-values | grep AKS_CLUSTER_NAME | cut -d'=' -f2 | tr -d '"')
export RESOURCE_GROUP=$(azd env get-values | grep AZURE_RESOURCE_GROUP_NAME | cut -d'=' -f2 | tr -d '"')

az aks get-credentials --resource-group $RESOURCE_GROUP --name $AKS_CLUSTER_NAME
```

### Step 3: Install Kaito Operator

```bash
# Install Kaito on AKS
./scripts/install-kaito.sh

# Verify installation
kubectl get pods -n kaito-system
```

### Step 4: Build and Deploy MCP Server

```bash
# Set environment variables
export CONTAINER_REGISTRY=$(azd env get-values | grep CONTAINER_REGISTRY | cut -d'=' -f2 | tr -d '"')
export AZURE_STORAGE_ACCOUNT_URL=$(azd env get-values | grep AZURE_STORAGE_ACCOUNT_URL | cut -d'=' -f2 | tr -d '"')
export AZURE_CLIENT_ID=$(azd env get-values | grep MCP_SERVER_IDENTITY_CLIENT_ID | cut -d'=' -f2 | tr -d '"')

# Build and push Docker image
./scripts/build-and-push.sh

# Deploy to Kubernetes
export IMAGE_TAG=latest
envsubst < k8s/mcp-server-deployment.yaml | kubectl apply -f -
```

### Step 5: Deploy Azure Foundry Model

```bash
# Deploy Phi-3 model using Kaito
kubectl apply -f k8s/kaito-foundry-workspace.yaml

# Wait for model to be ready (5-10 minutes)
kubectl wait --for=condition=Ready workspace/azure-foundry-model --timeout=15m

# Check status
kubectl get workspace
```

### Step 6: Test Your Setup

```bash
# Run tests
python tests/test_mcp_fixed_session.py

# Or use MCP Inspector
npx @modelcontextprotocol/inspector
```

## 🔧 Configuration

### Using Different Azure Foundry Models

Edit `k8s/kaito-foundry-workspace.yaml`:

```yaml
spec:
  inference:
    preset:
      name: phi-3-mini-128k-instruct  # Change model here
  resource:
    instanceType: Standard_NC6s_v3  # Adjust VM size for larger models
```

Supported models:
- `phi-3-mini-4k-instruct` (recommended for testing)
- `phi-3-mini-128k-instruct`
- `phi-3-medium`
- Other Azure Foundry models

### Custom MCP Tools

Add new tools in `src/mcp_server.py`:

```python
TOOLS.append(
    MCPTool(
        name="my_tool",
        description="What this tool does",
        inputSchema={
            "type": "object",
            "properties": {
                "param1": {"type": "string", "description": "..."}
            },
            "required": ["param1"]
        }
    )
)

# Implement in execute_tool()
async def execute_tool(tool_name: str, arguments: Dict[str, Any]):
    if tool_name == "my_tool":
        # Your implementation
        return MCPToolResult(content=[{"type": "text", "text": "Result"}])
```  


## 🧪 Testing

### Automated Tests

```bash
# Run MCP server tests
python tests/test_mcp_fixed_session.py

# Test Kaito deployment
kubectl get workspace
kubectl describe workspace azure-foundry-model
```

### Manual Testing with MCP Inspector

```bash
npx @modelcontextprotocol/inspector
```

In MCP Inspector:
1. Set transport to **SSE**
2. Enter: `https://<your-apim>.azure-api.net/mcp/sse`
3. Add Authorization header
4. Click **Connect** → **List Tools**

## 📊 Monitoring

```bash
# MCP server logs
kubectl logs -n mcp-server -l app=mcp-server --follow

# Kaito operator logs
kubectl logs -n kaito-system -l app=kaito --follow

# Model logs
kubectl logs -l kaito.sh/workspace=azure-foundry-model
```

## 🛠️ Troubleshooting

### AKS Issues

```bash
# Check nodes
kubectl get nodes

# Check GPU availability
kubectl describe node -l workload=gpu
```

### Kaito Issues

```bash
# Check Kaito status
kubectl get pods -n kaito-system

# Check workspace
kubectl describe workspace azure-foundry-model

# Scale GPU nodes manually if needed
az aks nodepool scale --resource-group $RESOURCE_GROUP \
  --cluster-name $AKS_CLUSTER_NAME --name gpupool --node-count 1
```

### MCP Server Issues

```bash
# Check pods
kubectl get pods -n mcp-server

# View logs
kubectl logs -n mcp-server -l app=mcp-server

# Restart deployment
kubectl rollout restart deployment/mcp-server -n mcp-server
```

## 💰 Cost Optimization

### Auto-Scale GPU to Zero

GPU nodes scale to 0 when idle (configured by default):

```yaml
# In kaito-foundry-workspace.yaml
spec:
  resource:
    count: 0  # Scales to zero when not in use
```

### Use Spot Instances

Edit `infra/core/aks/aks-cluster.bicep` to use spot VMs (70-90% cost reduction):

```bicep
scaleSetPriority: 'Spot'
scaleSetEvictionPolicy: 'Delete'
spotMaxPrice: -1  # Pay up to regular price
```

## 🔐 Security

- **Authentication**: OAuth 2.0 via Azure Entra ID
- **Workload Identity**: Pod-level managed identities
- **Network**: Optional VNet isolation (`vnetEnabled=true`)
- **RBAC**: Kubernetes and Azure RBAC enabled
- **Data Encryption**: Cosmos DB and Azure Storage encryption at rest
- **Access Control**: Azure AI Search and Foundry Agent Service ACLs

## 🧠 Central Memory & Foundry IQ

### Long-term Memory with Cosmos DB

The MCP server automatically stores conversation threads and tool execution traces in Cosmos DB:

```python
# Thread storage happens automatically
# Retrieve conversation history
from cosmos_memory_client import create_cosmos_memory_client

memory_client = create_cosmos_memory_client()
history = await memory_client.get_thread_history(
    agent_id="my-agent",
    thread_id="conversation-123"
)
```

**Environment Variables:**
```bash
export COSMOS_DB_ENDPOINT="https://your-cosmos.documents.azure.com:443/"
export COSMOS_DB_DATABASE_NAME="agents-memory"
export COSMOS_DB_THREADS_CONTAINER="threads"
export COSMOS_DB_TRACES_CONTAINER="tool-traces"
```

### Agentic Search with Foundry IQ

Use the `foundry_iq_search` tool for intelligent knowledge retrieval:

```json
{
  "tool": "foundry_iq_search",
  "arguments": {
    "query": "How do I deploy a new model?",
    "top": 5,
    "category": "documentation"
  }
}
```

**Indexing Documents:**
```python
from foundry_iq_client import create_foundry_iq_client

foundry_iq = create_foundry_iq_client()
await foundry_iq.index_document(
    doc_id="doc-123",
    content="Your document content here",
    title="Document Title",
    category="documentation"
)
```

**Environment Variables:**
```bash
export AZURE_SEARCH_ENDPOINT="https://your-search.search.windows.net"
export AZURE_SEARCH_INDEX_NAME="agent-knowledge-base"
```

### Multi-Agent Orchestration

Register your MCP tools with Azure AI Foundry Agent Service for multi-agent coordination:

```bash
# Register tools
python -m tool_registry sync \
  --mcp-endpoint "https://your-apim.azure-api.net/mcp" \
  --ai-project-endpoint "https://your-project.api.azureml.ms"
```

See [Tool Registry Documentation](docs/TOOL_REGISTRY.md) for details.

**Environment Variables:**
```bash
export AI_PROJECT_ENDPOINT="https://your-project.api.azureml.ms"
export AI_PROJECT_NAME="your-project-name"
export MCP_ENDPOINT_URL="https://your-apim.azure-api.net/mcp"
```

## 📚 Learn More

- [Kaito Project](https://github.com/kaito-project/kaito) - Kubernetes AI Toolchain Operator
- [Azure Kubernetes Service](https://learn.microsoft.com/azure/aks/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Azure AI Foundry](https://learn.microsoft.com/azure/ai-studio/)
- [Azure AI Agent Service](https://learn.microsoft.com/azure/ai-studio/concepts/agents)
- [Azure API Management](https://learn.microsoft.com/azure/api-management/)
- [Azure Cosmos DB](https://learn.microsoft.com/azure/cosmos-db/)
- [Azure AI Search](https://learn.microsoft.com/azure/search/)
- [Tool Registry Documentation](docs/TOOL_REGISTRY.md) - Multi-agent orchestration guide

## 🤝 Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

This project is licensed under the MIT License - see [LICENSE.md](LICENSE.md).
