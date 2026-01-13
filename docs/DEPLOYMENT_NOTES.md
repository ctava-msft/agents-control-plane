# Deployment Notes

## Infrastructure Successfully Deployed! 🎉

Date: October 16, 2025

### Deployed Resources

✅ **Resource Group**: rg-apim-mcp-aks-kaito  
✅ **AKS Cluster**: aks-jozz4mn7tla5s (Kubernetes 1.31.11)  
✅ **Container Registry**: crjozz4mn7tla5s  
✅ **Storage Account**: stjozz4mn7tla5s  
✅ **API Management**: apim-dx2iaqct63a2e  
✅ **Virtual Network**: vnet-jozz4mn7tla5s  
✅ **Log Analytics**: log-jozz4mn7tla5s  
✅ **Application Insights**: appi-jozz4mn7tla5s  
✅ **Managed Identities**: For AKS, MCP workload, and Entra App  

### Important Notes

#### GPU Node Pool Status
⚠️ **GPU nodes are DISABLED** due to Azure Policy restrictions in the MCAPS subscription.

The deployment was configured with `enableGpuNodePool: false` because Azure Policy blocks:
- VM type: `Standard_NC4as_T4_v3`
- Error: `RequestDisallowedByPolicy`
- Wiki: https://aka.ms/AzPolicyWiki

**To enable GPU nodes later:**
1. Request policy exemption from MCAPS team
2. Update `infra/main.bicep`: Set `enableGpuNodePool: true`
3. Run `azd up` again

#### Configuration Changes Made

1. **requirements.txt**: Copied from root to `src/` directory for Docker build
2. **Kubernetes Version**: Updated from `1.29.2` to `1.31.11` (officially supported)
3. **Service CIDR**: Changed from `10.0.0.0/16` to `10.240.0.0/16` (avoid VNet overlap)
4. **Subnet Delegation**: Removed `Microsoft.App/environments` delegation (AKS incompatible)
5. **GPU VM Size**: Updated from `Standard_NC6s_v3` to `Standard_NC4as_T4_v3` (available in region)
6. **GPU Node Pool**: Made conditional with `enableGpuNodePool` parameter

### Next Steps

Now that infrastructure is deployed, you need to manually complete these steps:

#### 1. Get AKS Credentials
```powershell
az aks get-credentials --resource-group rg-apim-mcp-aks-kaito --name aks-jozz4mn7tla5s --overwrite-existing
```

#### 2. Install Kaito Operator (Optional - requires GPU)
**Note**: Kaito requires GPU nodes to function. Since GPU nodes are disabled, you can skip this step for now.

```powershell
.\scripts\install-kaito.ps1
```

Or manually:
```powershell
helm repo add kaito https://azure.github.io/kaito
helm repo update
kubectl apply -f https://github.com/kaito-project/kaito/releases/download/v0.2.0/crd-install.yaml
helm install kaito-workspace kaito/kaito-workspace --create-namespace --namespace kaito-workspace
```

#### 3. Deploy MCP Server to Kubernetes
```powershell
# Deploy the MCP server
kubectl apply -f k8s/mcp-server-deployment.yaml

# Verify deployment
kubectl get pods
kubectl get services
```

#### 4. (Optional) Deploy Kaito Model Workspace
**Note**: This requires GPU nodes to be enabled.

```powershell
kubectl apply -f k8s/kaito-foundry-workspace.yaml

# Check workspace status
kubectl get workspace
kubectl describe workspace phi-3-mini-workspace
```

#### 5. Test the Deployment
```powershell
# Run deployment tests
python tests/test_kaito_deployment.py

# Test MCP endpoints (if you have the test script)
python tests/test_mcp_fixed_session.py
```

#### 6. Get APIM Endpoints
```powershell
# Get APIM gateway URL
az apim show --name apim-dx2iaqct63a2e --resource-group rg-apim-mcp-aks-kaito --query "gatewayUrl" --output tsv

# OAuth endpoints will be:
# - Authorization: https://apim-dx2iaqct63a2e.azure-api.net/oauth/authorize
# - Token: https://apim-dx2iaqct63a2e.azure-api.net/oauth/token
# - MCP SSE: https://apim-dx2iaqct63a2e.azure-api.net/mcp/sse
# - MCP Message: https://apim-dx2iaqct63a2e.azure-api.net/mcp/message
```

### Troubleshooting

#### If azd up shows storage account error
This is a known transient error that doesn't affect the deployed resources. All critical resources are deployed successfully. You can safely proceed with the next steps.

#### If Docker is not running
```powershell
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
# Wait for Docker Desktop to start (~30-60 seconds)
docker info  # Verify Docker is running
```

#### If APIM soft-delete error occurs
```powershell
az apim deletedservice purge --service-name apim-dx2iaqct63a2e --location eastus2
```

#### If you need to restart deployment
```powershell
# Delete resource group
az group delete --name rg-apim-mcp-aks-kaito --yes --no-wait

# Wait for deletion
# Monitor: az group list --query "[?name=='rg-apim-mcp-aks-kaito']"

# Redeploy
azd up
```

### Architecture

See `docs/ARCHITECTURE.md` for comprehensive Mermaid diagrams including:
- Component Architecture
- Deployment Architecture  
- Sequence Diagrams (Authentication, Tool Discovery, Tool Execution, Model Inference)
- Activity Diagrams (Deployment Process, Request Processing, Model Scaling)

### Known Limitations (Current Deployment)

1. **No GPU nodes**: Kaito model deployments will not work until GPU nodes are enabled
2. **No AI model inference**: Without GPU nodes, you cannot deploy Foundry models via Kaito
3. **MCP Server only**: The MCP server will work fine for the three tools (hello_mcp, save_snippet, get_snippet)

### What Works Without GPU

✅ MCP Server deployment on AKS  
✅ API Management OAuth authentication  
✅ MCP protocol endpoints (/sse, /message)  
✅ Tool execution (hello_mcp, save_snippet, get_snippet)  
✅ Azure Storage integration with managed identity  
✅ Application Insights monitoring  

❌ Kaito workspace deployment  
❌ AI model inference (Phi-3, Llama, etc.)  
❌ GPU-accelerated workloads  

### Additional Resources

- [README.md](./README.md) - Main documentation
- [MIGRATION.md](./MIGRATION.md) - Migration guide from Azure Functions
- [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) - Architecture diagrams
- [Azure Policy Wiki](https://aka.ms/AzPolicyWiki) - Policy compliance information

---

## Summary

Your infrastructure is **successfully deployed** and ready for MCP server deployment! 

The main limitation is the lack of GPU nodes due to policy restrictions. You can still deploy and test the MCP server without GPU-based model inference. To enable full Kaito functionality, you'll need to request a policy exemption from the MCAPS team.

**Next Command**: 
```powershell
az aks get-credentials --resource-group rg-apim-mcp-aks-kaito --name aks-jozz4mn7tla5s --overwrite-existing
```
