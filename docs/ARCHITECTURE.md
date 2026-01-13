# System Architecture Diagrams

This document provides comprehensive Mermaid diagrams for the AI Agents with AKS, Kaito, and APIM solution.

## Table of Contents

1. [Component Architecture Diagram](#component-architecture-diagram)
2. [Detailed Component Diagram](#detailed-component-diagram)
3. [Deployment Architecture](#deployment-architecture)
4. [Sequence Diagrams](#sequence-diagrams)
   - [Agent Authentication Flow](#agent-authentication-flow)
   - [MCP Tool Discovery](#mcp-tool-discovery)
   - [MCP Tool Execution](#mcp-tool-execution)
   - [Model Inference with Kaito](#model-inference-with-kaito)
5. [Activity Diagrams](#activity-diagrams)
   - [Deployment Process](#deployment-process-activity-diagram)
   - [Request Processing](#request-processing-activity-diagram)
   - [Kaito Model Scaling](#kaito-model-scaling-activity-diagram)

---

## Component Architecture Diagram

High-level component view of the entire system:

```mermaid
graph TB
    subgraph "Client Layer"
        Agent[AI Agent<br/>Claude/ChatGPT/Custom]
        Inspector[MCP Inspector<br/>Testing Tool]
    end

    subgraph "Azure API Management"
        APIM[APIM Gateway<br/>OAuth + Routing]
        OAuthAPI[OAuth API<br/>/authorize, /token]
        MCPAPI[MCP API<br/>/sse, /message]
    end

    subgraph "Azure Kubernetes Service"
        subgraph "System Node Pool"
            MCPPod1[MCP Server Pod 1]
            MCPPod2[MCP Server Pod 2]
        end
        
        subgraph "GPU Node Pool"
            KaitoOp[Kaito Operator]
            ModelPod[Foundry Model Pod<br/>Phi-3/Llama]
        end
        
        MCPSvc[MCP Server Service<br/>ClusterIP]
    end

    subgraph "Azure Services"
        ACR[Azure Container<br/>Registry]
        Storage[Azure Blob<br/>Storage]
        AppInsights[Application<br/>Insights]
        EntraID[Azure Entra ID<br/>OAuth Provider]
    end

    Agent --> APIM
    Inspector --> APIM
    APIM --> OAuthAPI
    APIM --> MCPAPI
    OAuthAPI --> EntraID
    MCPAPI --> MCPSvc
    MCPSvc --> MCPPod1
    MCPSvc --> MCPPod2
    MCPPod1 --> Storage
    MCPPod2 --> Storage
    MCPPod1 -.Optional.-> ModelPod
    MCPPod2 -.Optional.-> ModelPod
    KaitoOp --> ModelPod
    KaitoOp --> ACR
    MCPPod1 --> AppInsights
    MCPPod2 --> AppInsights

    style Agent fill:#e1f5ff
    style APIM fill:#fff4e6
    style MCPPod1 fill:#e8f5e9
    style MCPPod2 fill:#e8f5e9
    style ModelPod fill:#f3e5f5
    style KaitoOp fill:#f3e5f5
```

---

## Detailed Component Diagram

Detailed view showing all components, their responsibilities, and interactions:

```mermaid
graph TB
    subgraph "AI Agent Client"
        AgentCore[Agent Core Engine]
        MCPClient[MCP Client Library]
        AgentCore --> MCPClient
    end

    subgraph "Azure API Management Layer"
        subgraph "OAuth Components"
            AuthEndpoint[/authorize Endpoint]
            TokenEndpoint[/token Endpoint]
            RegisterEndpoint[/register Endpoint]
            WellKnown[/.well-known<br/>OAuth Metadata]
        end
        
        subgraph "MCP Components"
            SSEEndpoint[/sse Endpoint<br/>Server-Sent Events]
            MessageEndpoint[/message Endpoint<br/>JSON-RPC 2.0]
        end
        
        subgraph "APIM Policies"
            AuthPolicy[Authentication Policy<br/>OAuth Token Validation]
            RateLimitPolicy[Rate Limiting Policy]
            CORSPolicy[CORS Policy]
            BackendPolicy[Backend Routing Policy]
        end
    end

    subgraph "AKS Cluster - System Node Pool"
        subgraph "MCP Server Deployment"
            subgraph "Pod 1"
                FastAPI1[FastAPI App]
                SSEHandler1[SSE Handler<br/>Async Streaming]
                MCPTools1[MCP Tool Executor<br/>hello, get, save]
                StorageClient1[Azure Storage SDK]
            end
            
            subgraph "Pod 2"
                FastAPI2[FastAPI App]
                SSEHandler2[SSE Handler]
                MCPTools2[MCP Tool Executor]
                StorageClient2[Azure Storage SDK]
            end
        end
        
        K8sService[Kubernetes Service<br/>Load Balancer]
        ServiceAccount[Service Account<br/>Workload Identity]
    end

    subgraph "AKS Cluster - GPU Node Pool"
        subgraph "Kaito Components"
            KaitoController[Kaito Controller<br/>Workspace Manager]
            KaitoCRD[Workspace CRD<br/>Custom Resource]
        end
        
        subgraph "Model Inference"
            ModelServer[vLLM/TGI Server<br/>Model Serving]
            GPUResources[NVIDIA GPU<br/>NC-Series VM]
            ModelCache[Model Weights<br/>Cached Locally]
        end
    end

    subgraph "Azure Container Registry"
        MCPImage[MCP Server Image<br/>mcp-server:latest]
        FoundryImage[Foundry Model Image<br/>phi-3-mini-4k]
    end

    subgraph "Azure Storage"
        SnippetsContainer[snippets Container<br/>Blob Storage]
        DeploymentContainer[deployment Container<br/>Code Packages]
    end

    subgraph "Monitoring & Identity"
        AppInsightsSDK[App Insights SDK<br/>Telemetry]
        ManagedIdentity[Managed Identity<br/>AAD Integration]
        LogAnalytics[Log Analytics<br/>Workspace]
    end

    MCPClient --> SSEEndpoint
    MCPClient --> MessageEndpoint
    SSEEndpoint --> AuthPolicy
    MessageEndpoint --> AuthPolicy
    AuthPolicy --> RateLimitPolicy
    RateLimitPolicy --> BackendPolicy
    BackendPolicy --> K8sService
    
    K8sService --> FastAPI1
    K8sService --> FastAPI2
    
    FastAPI1 --> SSEHandler1
    FastAPI1 --> MCPTools1
    MCPTools1 --> StorageClient1
    StorageClient1 --> SnippetsContainer
    
    FastAPI2 --> SSEHandler2
    FastAPI2 --> MCPTools2
    MCPTools2 --> StorageClient2
    StorageClient2 --> SnippetsContainer
    
    ServiceAccount --> ManagedIdentity
    ManagedIdentity --> SnippetsContainer
    
    KaitoController --> KaitoCRD
    KaitoCRD --> ModelServer
    ModelServer --> GPUResources
    ModelServer --> ModelCache
    
    KaitoController --> ACR
    ACR --> FoundryImage
    ACR --> MCPImage
    
    FastAPI1 --> AppInsightsSDK
    FastAPI2 --> AppInsightsSDK
    AppInsightsSDK --> LogAnalytics
    
    AuthEndpoint --> ManagedIdentity

    style AgentCore fill:#e1f5ff
    style APIM fill:#fff4e6
    style FastAPI1 fill:#e8f5e9
    style FastAPI2 fill:#e8f5e9
    style ModelServer fill:#f3e5f5
    style GPUResources fill:#ffebee
```

---

## Deployment Architecture

Infrastructure and deployment view:

```mermaid
graph TB
    subgraph "Azure Subscription"
        subgraph "Resource Group"
            subgraph "Network Layer"
                VNet[Virtual Network<br/>Optional]
                SystemSubnet[System Subnet<br/>10.240.0.0/16]
                GPUSubnet[GPU Subnet<br/>10.241.0.0/16]
            end
            
            subgraph "Compute Layer"
                AKS[AKS Cluster<br/>Managed Kubernetes]
                SystemNodePool[System Node Pool<br/>Standard_DS2_v2<br/>Min: 2, Max: 4]
                GPUNodePool[GPU Node Pool<br/>Standard_NC6s_v3<br/>Min: 0, Max: 3]
            end
            
            subgraph "Container Services"
                ACR[Azure Container Registry<br/>Standard SKU]
            end
            
            subgraph "API Layer"
                APIM[API Management<br/>Developer/Standard Tier]
            end
            
            subgraph "Storage Layer"
                StorageAcct[Storage Account<br/>Standard_LRS]
                BlobService[Blob Service<br/>snippets container]
            end
            
            subgraph "Monitoring Layer"
                LogWorkspace[Log Analytics Workspace]
                AppInsights[Application Insights]
            end
            
            subgraph "Identity Layer"
                AKSIdentity[AKS Managed Identity]
                MCPIdentity[MCP Workload Identity]
                APIMIdentity[APIM Managed Identity]
            end
        end
    end

    AKS --> SystemNodePool
    AKS --> GPUNodePool
    SystemNodePool --> SystemSubnet
    GPUNodePool --> GPUSubnet
    
    AKS --> AKSIdentity
    AKS --> ACR
    
    APIM --> AKS
    APIM --> APIMIdentity
    
    SystemNodePool --> StorageAcct
    StorageAcct --> BlobService
    
    MCPIdentity --> BlobService
    
    AKS --> AppInsights
    AppInsights --> LogWorkspace
    
    ACR --> AKSIdentity

    style AKS fill:#326ce5,color:#fff
    style SystemNodePool fill:#326ce5,color:#fff
    style GPUNodePool fill:#76b900,color:#fff
    style APIM fill:#0078d4,color:#fff
    style ACR fill:#0078d4,color:#fff
    style StorageAcct fill:#0078d4,color:#fff
```

---

## Sequence Diagrams

### Agent Authentication Flow

OAuth 2.0 PKCE flow for AI agent authentication:

```mermaid
sequenceDiagram
    participant Agent as AI Agent
    participant APIM as Azure APIM<br/>OAuth API
    participant Entra as Azure Entra ID
    participant Session as Session Store

    Note over Agent,Entra: Initial Authentication (OAuth 2.0 + PKCE)
    
    Agent->>Agent: Generate code_verifier<br/>Generate code_challenge
    
    Agent->>APIM: GET /oauth/authorize<br/>?code_challenge=xxx
    APIM->>Entra: Redirect to Entra ID Login
    
    Entra->>Entra: User Authentication
    Entra-->>APIM: Authorization code
    APIM-->>Agent: Authorization code
    
    Agent->>APIM: POST /oauth/token<br/>code + code_verifier
    APIM->>Entra: Validate code_verifier<br/>against code_challenge
    Entra-->>APIM: Validation success
    
    APIM->>APIM: Generate mcp_access_token
    APIM->>Session: Store session
    Session-->>APIM: Session ID
    
    APIM-->>Agent: {<br/>  access_token: "mcp_access_token_xxx",<br/>  expires_in: 3600<br/>}
    
    Note over Agent,Session: Agent is now authenticated
```

### MCP Tool Discovery

AI agent discovers available tools:

```mermaid
sequenceDiagram
    participant Agent as AI Agent
    participant APIM as Azure APIM<br/>MCP API
    participant K8s as AKS Service
    participant MCP as MCP Server Pod
    participant Session as Session Manager

    Note over Agent,Session: SSE Session Establishment
    
    Agent->>APIM: GET /mcp/sse<br/>Authorization: Bearer mcp_access_token_xxx
    APIM->>APIM: Validate OAuth token
    
    APIM->>K8s: Forward to /runtime/webhooks/mcp/sse
    K8s->>MCP: Route to available pod
    
    MCP->>MCP: Generate session_id
    MCP->>Session: Create session
    Session-->>MCP: Session created
    
    MCP-->>Agent: SSE Stream opened<br/>data: message?sessionId=abc123
    
    Note over Agent,Session: Tool Discovery
    
    Agent->>APIM: POST /mcp/message<br/>{method: "tools/list"}
    APIM->>K8s: Forward request
    K8s->>MCP: Route to same pod (session affinity)
    
    MCP->>MCP: Get tool definitions
    
    MCP-->>K8s: {tools: [<br/>  {name: "hello_mcp", ...},<br/>  {name: "save_snippet", ...},<br/>  {name: "get_snippet", ...}<br/>]}
    
    K8s-->>APIM: Tool list response
    APIM-->>Agent: Tool list response
    
    Note over Agent: Agent now knows available tools
```

### MCP Tool Execution

AI agent executes a tool (save_snippet example):

```mermaid
sequenceDiagram
    participant Agent as AI Agent
    participant APIM as Azure APIM
    participant MCP as MCP Server Pod
    participant Storage as Azure Blob Storage
    participant Identity as Workload Identity
    participant Insights as App Insights

    Note over Agent,Insights: Tool Execution Request
    
    Agent->>APIM: POST /mcp/message<br/>{<br/>  method: "tools/call",<br/>  params: {<br/>    name: "save_snippet",<br/>    arguments: {<br/>      snippetname: "example",<br/>      snippet: "def hello()..."<br/>    }<br/>  }<br/>}
    
    APIM->>APIM: Validate token<br/>Check rate limits
    APIM->>MCP: Forward request
    
    MCP->>MCP: Parse tool request<br/>Validate parameters
    
    MCP->>Insights: Log: Tool execution started
    
    alt Storage Access with Managed Identity
        MCP->>Identity: Request Azure AD token
        Identity-->>MCP: Access token
        
        MCP->>Storage: PUT blob<br/>container: snippets<br/>blob: example.json<br/>content: "def hello()..."
        Storage-->>MCP: 201 Created
    else Direct Connection String (dev)
        MCP->>Storage: PUT with connection string
        Storage-->>MCP: 201 Created
    end
    
    MCP->>MCP: Build success response
    
    MCP->>Insights: Log: Tool execution completed<br/>Duration: 150ms
    
    MCP-->>APIM: {<br/>  content: [{<br/>    type: "text",<br/>    text: "Snippet saved successfully"<br/>  }],<br/>  isError: false<br/>}
    
    APIM-->>Agent: Tool execution result
    
    Agent->>Agent: Process result<br/>Continue reasoning
```

### Model Inference with Kaito

How Kaito manages and scales AI models:

```mermaid
sequenceDiagram
    participant User as Developer
    participant Kubectl as kubectl
    participant K8sAPI as Kubernetes API
    participant Kaito as Kaito Operator
    participant NodePool as GPU Node Pool
    participant ACR as Azure Container Registry
    participant ModelPod as Model Pod
    participant vLLM as vLLM Server

    Note over User,vLLM: Deploy Model with Kaito
    
    User->>Kubectl: kubectl apply -f<br/>kaito-foundry-workspace.yaml
    Kubectl->>K8sAPI: Create Workspace CRD
    K8sAPI->>Kaito: Watch: New Workspace
    
    Kaito->>Kaito: Parse Workspace spec<br/>Model: phi-3-mini-4k<br/>Instance: Standard_NC6s_v3<br/>Count: 1
    
    alt GPU Nodes Not Available
        Kaito->>NodePool: Check GPU node availability
        NodePool-->>Kaito: No nodes available
        
        Kaito->>NodePool: Scale up GPU node pool
        Note over NodePool: VM provisioning (~5 min)
        NodePool-->>Kaito: Node ready
    end
    
    Kaito->>ACR: Pull model image<br/>phi-3-mini-4k-instruct
    ACR-->>Kaito: Image pulled
    
    Kaito->>K8sAPI: Create Pod with:<br/>- GPU resources<br/>- Node selector: kaito=true<br/>- Tolerations for GPU taint
    
    K8sAPI->>ModelPod: Schedule on GPU node
    
    ModelPod->>ModelPod: Download model weights<br/>(if not cached)
    Note over ModelPod: ~2-5 GB download
    
    ModelPod->>vLLM: Start vLLM server<br/>Load model into GPU memory
    Note over vLLM: Model warming up
    
    vLLM-->>ModelPod: Ready
    ModelPod-->>K8sAPI: Pod Running
    K8sAPI->>Kaito: Pod status update
    
    Kaito->>K8sAPI: Update Workspace status<br/>Condition: Ready=True
    K8sAPI-->>User: Workspace Ready
    
    Note over User,vLLM: Model is ready for inference
    
    alt Idle Timeout (Optional)
        Note over vLLM: No requests for 30 min
        Kaito->>K8sAPI: Scale workspace to 0
        K8sAPI->>ModelPod: Terminate pod
        K8sAPI->>NodePool: Scale down GPU nodes
        Note over NodePool: Cost savings
    end
```

---

## Activity Diagrams

### Deployment Process Activity Diagram

Complete deployment workflow:

```mermaid
flowchart TD
    Start([Start Deployment]) --> PreReq{Prerequisites<br/>Installed?}
    
    PreReq -->|No| InstallTools[Install:<br/>- Azure CLI<br/>- azd<br/>- kubectl<br/>- helm<br/>- Docker]
    InstallTools --> PreReq
    
    PreReq -->|Yes| AzdInit[Run: azd init]
    AzdInit --> SetEnv[Select/Create<br/>Environment]
    SetEnv --> AzdUp[Run: azd up]
    
    AzdUp --> ProvInfra{Infrastructure<br/>Provision Success?}
    
    ProvInfra -->|No| CheckErrors[Check Errors:<br/>- Quota limits<br/>- Region availability<br/>- Permissions]
    CheckErrors --> AzdUp
    
    ProvInfra -->|Yes| InfraReady[Infrastructure Ready:<br/>✓ AKS Cluster<br/>✓ ACR<br/>✓ APIM<br/>✓ Storage<br/>✓ Monitoring]
    
    InfraReady --> GetCreds[azd post-provision:<br/>Get AKS credentials]
    GetCreds --> InstallKaito[Run:<br/>./scripts/install-kaito.sh]
    
    InstallKaito --> KaitoCheck{Kaito Operator<br/>Running?}
    
    KaitoCheck -->|No| WaitKaito[Wait 30s<br/>Check pods]
    WaitKaito --> KaitoCheck
    
    KaitoCheck -->|Yes| BuildImage[Run:<br/>./scripts/build-and-push.sh]
    BuildImage --> ImagePush[Push to ACR]
    
    ImagePush --> DeployMCP[kubectl apply:<br/>mcp-server-deployment.yaml]
    DeployMCP --> MCPCheck{MCP Server<br/>Pods Ready?}
    
    MCPCheck -->|No| WaitMCP[Wait for pods<br/>Check logs]
    WaitMCP --> MCPCheck
    
    MCPCheck -->|Yes| DeployModel[kubectl apply:<br/>kaito-foundry-workspace.yaml]
    
    DeployModel --> GPUScale{GPU Nodes<br/>Available?}
    
    GPUScale -->|No| ScaleGPU[Kaito scales up<br/>GPU node pool]
    ScaleGPU --> WaitGPU[Wait 5-10 min<br/>for VM provisioning]
    WaitGPU --> GPUScale
    
    GPUScale -->|Yes| ModelDeploy[Kaito deploys<br/>Foundry model pod]
    
    ModelDeploy --> ModelReady{Model Pod<br/>Ready?}
    
    ModelReady -->|No| CheckModel[Check:<br/>- Image pull<br/>- GPU allocation<br/>- Model download]
    CheckModel --> ModelReady
    
    ModelReady -->|Yes| RunTests[Run Tests:<br/>- test_kaito_deployment.py<br/>- test_mcp_fixed_session.py]
    
    RunTests --> TestsPass{All Tests<br/>Pass?}
    
    TestsPass -->|No| Debug[Debug Issues:<br/>- Check logs<br/>- Verify connectivity<br/>- Check auth]
    Debug --> RunTests
    
    TestsPass -->|Yes| Complete([Deployment Complete<br/>System Ready])
    
    style Start fill:#4caf50,color:#fff
    style Complete fill:#4caf50,color:#fff
    style PreReq fill:#ff9800
    style ProvInfra fill:#ff9800
    style KaitoCheck fill:#ff9800
    style MCPCheck fill:#ff9800
    style GPUScale fill:#ff9800
    style ModelReady fill:#ff9800
    style TestsPass fill:#ff9800
```

### Request Processing Activity Diagram

How a request flows through the system:

```mermaid
flowchart TD
    Start([AI Agent Request]) --> HasToken{Has Valid<br/>Access Token?}
    
    HasToken -->|No| StartAuth[Initiate OAuth Flow]
    StartAuth --> CodeChallenge[Generate PKCE<br/>code_challenge]
    CodeChallenge --> Authorize[Call /oauth/authorize]
    Authorize --> UserLogin[User authenticates<br/>with Entra ID]
    UserLogin --> GetCode[Receive auth code]
    GetCode --> ExchangeToken[POST /oauth/token<br/>with code_verifier]
    ExchangeToken --> ReceiveToken[Receive access_token]
    ReceiveToken --> HasToken
    
    HasToken -->|Yes| ConnectSSE[Connect to<br/>/mcp/sse endpoint]
    
    ConnectSSE --> ValidateToken{APIM Validates<br/>Token?}
    
    ValidateToken -->|Invalid| Return401[Return 401<br/>Unauthorized]
    Return401 --> End([End])
    
    ValidateToken -->|Valid| CheckRateLimit{Within Rate<br/>Limits?}
    
    CheckRateLimit -->|No| Return429[Return 429<br/>Too Many Requests]
    Return429 --> End
    
    CheckRateLimit -->|Yes| ForwardAPIM[APIM forwards to<br/>AKS Service]
    
    ForwardAPIM --> LoadBalance{Load Balancer<br/>Select Pod}
    
    LoadBalance -->|Pod 1| MCP1[MCP Server Pod 1]
    LoadBalance -->|Pod 2| MCP2[MCP Server Pod 2]
    
    MCP1 --> CreateSession[Create SSE Session]
    MCP2 --> CreateSession
    
    CreateSession --> StreamOpen[Stream Connection<br/>Established]
    
    StreamOpen --> WaitRequest[Wait for<br/>JSON-RPC Request]
    
    WaitRequest --> ReqType{Request Type?}
    
    ReqType -->|tools/list| GetTools[Retrieve Tool<br/>Definitions]
    GetTools --> ReturnTools[Return tool list<br/>via SSE]
    ReturnTools --> WaitRequest
    
    ReqType -->|tools/call| ParseTool[Parse tool name<br/>and arguments]
    
    ParseTool --> ToolType{Which Tool?}
    
    ToolType -->|hello_mcp| SimpleResp[Return greeting<br/>message]
    SimpleResp --> LogMetric
    
    ToolType -->|save_snippet| GetToken[Get Managed<br/>Identity token]
    GetToken --> WriteBlog[Write to Azure<br/>Blob Storage]
    WriteBlog --> ConfirmSave[Return success<br/>confirmation]
    ConfirmSave --> LogMetric
    
    ToolType -->|get_snippet| GetToken2[Get Managed<br/>Identity token]
    GetToken2 --> ReadBlob[Read from Azure<br/>Blob Storage]
    ReadBlob --> ReturnSnippet[Return snippet<br/>content]
    ReturnSnippet --> LogMetric
    
    ToolType -->|custom| CallModel[Optional: Call<br/>Kaito Model]
    CallModel --> ModelInference[Model processes<br/>on GPU]
    ModelInference --> ModelResp[Return model<br/>response]
    ModelResp --> LogMetric
    
    LogMetric[Log to App Insights:<br/>- Duration<br/>- Success/Failure<br/>- Tool name] --> CheckMore{More Requests?}
    
    CheckMore -->|Yes| WaitRequest
    CheckMore -->|No| CloseSSE[Close SSE<br/>Connection]
    
    CloseSSE --> Cleanup[Cleanup session<br/>resources]
    Cleanup --> End
    
    style Start fill:#2196f3,color:#fff
    style End fill:#2196f3,color:#fff
    style ValidateToken fill:#ff9800
    style CheckRateLimit fill:#ff9800
    style ReqType fill:#ff9800
    style ToolType fill:#ff9800
    style CheckMore fill:#ff9800
```

### Kaito Model Scaling Activity Diagram

Auto-scaling behavior for GPU resources:

```mermaid
flowchart TD
    Start([Kaito Operator<br/>Monitoring]) --> CheckWorkspace[Check Workspace<br/>Desired State]
    
    CheckWorkspace --> DesiredCount{Desired<br/>Instance Count}
    
    DesiredCount -->|0| ScaleDown[Scale Down Mode]
    DesiredCount -->|> 0| ScaleUp[Scale Up Mode]
    
    ScaleDown --> HasPods{Model Pods<br/>Exist?}
    HasPods -->|No| NoAction1[No Action Needed]
    NoAction1 --> Wait1[Wait 30s]
    Wait1 --> Start
    
    HasPods -->|Yes| GracefulStop[Graceful Shutdown:<br/>- Drain connections<br/>- Save state]
    GracefulStop --> DeletePod[Delete Model Pod]
    DeletePod --> CheckNodes{GPU Nodes<br/>Still Needed?}
    
    CheckNodes -->|No| ScaleNodePool[Scale GPU Node Pool<br/>to 0]
    ScaleNodePool --> SaveCost[💰 Cost Savings:<br/>No GPU charges]
    SaveCost --> Wait1
    
    CheckNodes -->|Yes| OtherWorkloads[Other workloads<br/>using GPUs]
    OtherWorkloads --> Wait1
    
    ScaleUp --> CurrentPods{Current Pod<br/>Count}
    
    CurrentPods -->|= Desired| NoAction2[No Scaling Needed]
    NoAction2 --> MonitorHealth[Monitor Pod<br/>Health]
    MonitorHealth --> Wait2[Wait 30s]
    Wait2 --> Start
    
    CurrentPods -->|< Desired| CheckGPUNodes{Sufficient GPU<br/>Nodes?}
    
    CheckGPUNodes -->|No| CalcNeeded[Calculate Nodes<br/>Needed]
    CalcNeeded --> RequestScale[Request Node Pool<br/>Scale Up]
    
    RequestScale --> WaitNode[Wait for Azure<br/>VM Provisioning]
    Note1[⏱️ Typically 5-8 minutes]
    WaitNode --> Note1
    Note1 --> NodeReady{Node Ready?}
    
    NodeReady -->|No| CheckTimeout{Timeout<br/>Exceeded?}
    CheckTimeout -->|Yes| AlertError[Alert: Scaling<br/>Timeout]
    AlertError --> Wait1
    
    CheckTimeout -->|No| WaitNode
    
    NodeReady -->|Yes| LabelNode[Label Node:<br/>workload=gpu<br/>kaito=true]
    LabelNode --> CheckGPUNodes
    
    CheckGPUNodes -->|Yes| HasImage{Model Image<br/>in Cache?}
    
    HasImage -->|No| PullImage[Pull from ACR:<br/>Foundry Model Image]
    Note2[📦 ~2-5 GB]
    PullImage --> Note2
    Note2 --> DownloadWeights[Download Model<br/>Weights]
    Note3[📦 ~2-10 GB depending<br/>on model size]
    DownloadWeights --> Note3
    Note3 --> HasImage
    
    HasImage -->|Yes| CreatePod[Create Model Pod:<br/>- Assign to GPU node<br/>- Mount GPU device<br/>- Set resource limits]
    
    CreatePod --> InitContainer[Init Container:<br/>Verify GPU drivers<br/>Load model config]
    
    InitContainer --> StartVLLM[Start vLLM Server]
    StartVLLM --> LoadModel[Load Model into<br/>GPU Memory]
    
    LoadModel --> WarmUp[Model Warm-up:<br/>Test inference]
    WarmUp --> HealthCheck{Health Check<br/>Passing?}
    
    HealthCheck -->|No| RetryCount{Retry Count<br/>< Max?}
    RetryCount -->|Yes| RestartPod[Restart Pod]
    RestartPod --> StartVLLM
    
    RetryCount -->|No| FailedDeploy[Mark Workspace<br/>Failed]
    FailedDeploy --> Alert[Send Alert]
    Alert --> Wait1
    
    HealthCheck -->|Yes| UpdateStatus[Update Workspace<br/>Status: Ready]
    UpdateStatus --> ExposeService[Expose Model<br/>Service Endpoint]
    
    ExposeService --> MonitorMetrics[Monitor Metrics:<br/>- GPU utilization<br/>- Request latency<br/>- Error rate]
    
    MonitorMetrics --> Wait2
    
    style Start fill:#673ab7,color:#fff
    style ScaleDown fill:#ff5722,color:#fff
    style ScaleUp fill:#4caf50,color:#fff
    style HealthCheck fill:#ff9800
    style CheckGPUNodes fill:#ff9800
    style NodeReady fill:#ff9800
    style HasImage fill:#ff9800
    style SaveCost fill:#4caf50,color:#fff
```

---

## Legend

### Component Diagram Shapes

- **Rectangle**: Component or Service
- **Cylinder**: Database or Storage
- **Hexagon**: External Service
- **Diamond**: Decision Point
- **Rounded Rectangle**: Process or Function

### Sequence Diagram Notation

- **Solid Line →**: Synchronous Call
- **Dashed Line ⇢**: Response
- **Note**: Additional Information
- **Alt/Else**: Alternative Paths

### Activity Diagram Symbols

- **Rounded Rectangle**: Activity/Process
- **Diamond**: Decision Point
- **Circle**: Start/End Point
- **Rectangle**: Subprocess

---

## Viewing These Diagrams

These Mermaid diagrams can be rendered in:

1. **GitHub/GitLab**: Automatically renders in markdown files
2. **VS Code**: Install "Markdown Preview Mermaid Support" extension
3. **Mermaid Live Editor**: https://mermaid.live
4. **Documentation Sites**: Most support Mermaid natively

---

## Additional Resources

- [Mermaid Documentation](https://mermaid.js.org/)
- [Architecture Decision Records](./docs/adr/)
- [Deployment Guide](./README.md)
- [Migration Guide](./MIGRATION.md)
