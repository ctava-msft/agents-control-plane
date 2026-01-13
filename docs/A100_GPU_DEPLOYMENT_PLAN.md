# A100 GPU Deployment Plan

## Overview
This document provides a comprehensive inventory of changes required to deploy language models to an A100 GPU node pool in the existing AKS cluster (`rg-apim-mcp-aks-kaito`).

---

## Current State

### Existing Configuration
- **Resource Group**: `rg-apim-mcp-aks-kaito`
- **AKS Cluster**: `aks-jozz4mn7tla5s` (Kubernetes 1.31.11)
- **Current GPU Configuration**: 
  - GPU Node Pool: **DISABLED** (`enableGpuNodePool: false`)
  - Current VM Size: `Standard_NC4as_T4_v3` (NVIDIA T4 GPUs)
  - Min Count: 0
  - Max Count: 3
- **System Node Pool**: 2x `Standard_DS2_v2` nodes (non-GPU)
- **Kaito Status**: Operator not installed (prepared but deferred)
- **MCP Server**: 2 pods running on system nodes

### Known Constraints
- **Azure Policy**: MCAPS subscription has policy restrictions on GPU VM types
- **Previous Failure**: `Standard_NC4as_T4_v3` deployment failed with `RequestDisallowedByPolicy`

---

## A100 GPU Requirements

### VM Size Options for A100 GPUs

Azure offers several A100-based VM sizes. Choose based on your model size and performance requirements:

| VM Size | GPUs | GPU Memory | vCPUs | RAM | Cost Tier | Use Case |
|---------|------|------------|-------|-----|-----------|----------|
| **Standard_NC24ads_A100_v4** | 1x A100 (40GB) | 40 GB | 24 | 220 GB | $$ | Small-medium models (Phi-3, small Llama) |
| **Standard_NC48ads_A100_v4** | 2x A100 (40GB) | 80 GB | 48 | 440 GB | $$$ | Medium models (Llama 7B-13B) |
| **Standard_NC96ads_A100_v4** | 4x A100 (40GB) | 160 GB | 96 | 880 GB | $$$$ | Large models (Llama 70B) |
| **Standard_ND96asr_v4** | 8x A100 (40GB) | 320 GB | 96 | 900 GB | $$$$$ | Very large models, multi-GPU training |
| **Standard_ND96amsr_A100_v4** | 8x A100 (80GB) | 640 GB | 96 | 1900 GB | $$$$$$ | Largest models, extensive fine-tuning |

**Recommendation**: Start with `Standard_NC24ads_A100_v4` (1x A100 40GB) for cost-effectiveness and most Foundry models.

### Regional Availability

A100 VMs are available in limited regions. Check current availability:

```powershell
# Check A100 availability in your region
az vm list-skus --location eastus --size Standard_NC --all --output table | Select-String "A100"
az vm list-skus --location eastus2 --size Standard_NC --all --output table | Select-String "A100"
az vm list-skus --location westus2 --size Standard_NC --all --output table | Select-String "A100"
```

**Common A100 Regions**:
- East US
- East US 2
- West US 2
- South Central US
- West Europe
- North Europe

---

## Required Changes Inventory

### 1. Infrastructure Changes (Bicep)

#### 1.1 `infra/main.bicep`
**Current State**: GPU pool disabled with T4 configuration
**Required Changes**:

```bicep
// Lines 150-156: Update GPU VM size and enable GPU pool
module aksCluster './core/aks/aks-cluster.bicep' = {
  name: 'aksCluster'
  scope: rg
  params: {
    aksClusterName: '${abbrs.containerServiceManagedClusters}${resourceToken}'
    location: location
    tags: tags
    kubernetesVersion: '1.31.11'
    systemNodePoolVmSize: 'Standard_DS2_v2'
    systemNodePoolCount: 2
    
    // CHANGE 1: Update GPU VM size to A100
    gpuNodePoolVmSize: 'Standard_NC24ads_A100_v4'  // Changed from Standard_NC4as_T4_v3
    
    // CHANGE 2: Set minimum GPU nodes (start with 1 for cost)
    gpuNodePoolMinCount: 1  // Changed from 0
    
    // CHANGE 3: Increase max count for scaling
    gpuNodePoolMaxCount: 4  // Changed from 3 (adjust based on budget)
    
    // CHANGE 4: Enable GPU node pool
    enableGpuNodePool: true  // Changed from false
    
    userAssignedIdentityId: aksUserAssignedIdentity.outputs.identityId
    logAnalyticsWorkspaceId: monitoring.outputs.logAnalyticsWorkspaceId
    subnetId: vnetEnabled ? '${rg.id}/providers/Microsoft.Network/virtualNetworks/${serviceVirtualNetworkName}/subnets/${serviceVirtualNetworkAppSubnetName}' : ''
  }
  dependsOn: vnetEnabled ? [
    serviceVirtualNetworkEarly
  ] : []
}
```

**Action Items**:
- [ ] Change `gpuNodePoolVmSize` from `Standard_NC4as_T4_v3` to `Standard_NC24ads_A100_v4`
- [ ] Change `gpuNodePoolMinCount` from `0` to `1`
- [ ] Change `gpuNodePoolMaxCount` from `3` to `4` (or higher based on needs)
- [ ] Change `enableGpuNodePool` from `false` to `true`

---

#### 1.2 `infra/core/aks/aks-cluster.bicep`
**Current State**: Configured for T4 GPUs
**Required Changes**:

```bicep
// Lines 19-26: Update default GPU parameters
@description('GPU node pool VM size for Kaito workloads')
param gpuNodePoolVmSize string = 'Standard_NC24ads_A100_v4'  // Changed default

@description('GPU node pool min count')
param gpuNodePoolMinCount int = 1  // Changed from 0

@description('GPU node pool max count')
param gpuNodePoolMaxCount int = 4  // Changed from 3

// Lines 43-44: Consider enabling by default
@description('Enable GPU node pool (requires policy exemption in some subscriptions)')
param enableGpuNodePool bool = true  // Changed from false (optional)
```

**Action Items**:
- [ ] Update default `gpuNodePoolVmSize` parameter to A100 VM size
- [ ] Update default `gpuNodePoolMinCount` to `1`
- [ ] Update default `gpuNodePoolMaxCount` to `4`
- [ ] Optionally change default `enableGpuNodePool` to `true`

---

#### 1.3 `infra/main.parameters.json`
**Current State**: No GPU-specific parameters
**Required Changes**:

Add optional parameters to override defaults:

```json
{
  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {
    "environmentName": {
      "value": "${AZURE_ENV_NAME}"
    },
    "location": {
      "value": "${AZURE_LOCATION}"
    },
    "vnetEnabled": {
      "value": "${VNET_ENABLED=true}"
    },
    "apimSku": {
      "value": "Basicv2" 
    },
    "mcpEntraApplicationDisplayName": {
      "value": "MCP-OAuth-App"
    },
    "mcpEntraApplicationUniqueName": {
      "value": "mcp-oauth-app-${AZURE_ENV_NAME}"
    },
    "existingEntraAppId": {
      "value": "6441e54f-8149-487b-aac4-3a55a049a362"
    }
  }
}
```

**Note**: No changes required if using defaults in main.bicep. Only add if you want to override per-environment.

**Action Items**:
- [ ] No immediate changes required (parameters will be passed from main.bicep)

---

### 2. Kubernetes Manifest Changes

#### 2.1 `k8s/kaito-workspace.yaml`
**Current State**: Configured for T4 GPU (Standard_NC6s_v3)
**Required Changes**:

```yaml
apiVersion: kaito.sh/v1alpha1
kind: Workspace
metadata:
  name: phi-3-mini-workspace
  namespace: default
spec:
  # Model inference configuration
  inference:
    preset:
      # CHANGE 1: Update model to take advantage of A100 memory
      name: phi-3-medium-128k-instruct  # Upgrade from phi-3-mini-4k-instruct
      # A100 can handle larger context windows
  
  # Resource requirements
  resource:
    # CHANGE 2: Update instance count
    count: 1
    
    # CHANGE 3: Update to A100 VM size
    instanceType: Standard_NC24ads_A100_v4  # Changed from Standard_NC6s_v3
    
    # Node selector to target GPU node pool
    labelSelector:
      matchLabels:
        kaito: "true"
        workload: "gpu"  # Ensure this matches AKS node labels
```

**Action Items**:
- [ ] Update `instanceType` from `Standard_NC6s_v3` to `Standard_NC24ads_A100_v4`
- [ ] Consider upgrading model from `phi-3-mini-4k-instruct` to `phi-3-medium-128k-instruct`
- [ ] Verify `labelSelector` matches node labels in AKS cluster

---

#### 2.2 `k8s/kaito-foundry-workspace.yaml`
**Current State**: Configured for T4 GPU
**Required Changes**:

```yaml
apiVersion: kaito.sh/v1alpha1
kind: Workspace
metadata:
  name: azure-foundry-model
  namespace: default
  annotations:
    description: "Workspace for deploying Azure Foundry models via Kaito on A100"
spec:
  # Model inference configuration using Azure Foundry registry
  inference:
    preset:
      # CHANGE 1: Upgrade to larger model that benefits from A100
      name: llama-2-7b-chat  # or phi-3-medium, mistral-7b
      
    # CHANGE 2: Optional - Use custom image from Azure Foundry/ACR
    # template:
    #   image: <your-acr>.azurecr.io/foundry/llama-2-7b-chat:latest
    #   imagePullPolicy: IfNotPresent
  
  # Resource requirements for model deployment
  resource:
    # CHANGE 3: Instance count
    count: 1
    
    # CHANGE 4: Update to A100 VM size
    instanceType: Standard_NC24ads_A100_v4  # Changed from Standard_NC6s_v3
    
    # Label selector to target GPU node pool created by Bicep
    labelSelector:
      matchLabels:
        kaito: "true"
        workload: "gpu"
  
  # OPTIONAL: Tuning configuration for fine-tuning models
  # Uncomment if you want to fine-tune the model
  # tuning:
  #   preset:
  #     name: llama-2-7b-chat
  #   method: qlora  # or lora
  #   input: azureml://subscriptions/<sub-id>/resourcegroups/<rg>/workspaces/<ws>/data/<dataset>
  #   config: |
  #     learning_rate: 0.0002
  #     num_train_epochs: 3
  #     per_device_train_batch_size: 4
  #     gradient_accumulation_steps: 4
```

**Action Items**:
- [ ] Update `instanceType` from `Standard_NC6s_v3` to `Standard_NC24ads_A100_v4`
- [ ] Consider upgrading to larger model (llama-2-7b, phi-3-medium, mistral-7b)
- [ ] Verify Azure Foundry registry integration (ACR connection)
- [ ] Optional: Configure model fine-tuning parameters

---

### 3. Azure Policy & Permissions

#### 3.1 Policy Exemption Request
**Current Blocker**: Azure Policy in MCAPS subscription blocks GPU VM deployment

**Action Items**:
- [ ] Submit policy exemption request at https://aka.ms/AzPolicyWiki
- [ ] Request exemption for **VM SKU**: `Standard_NC24ads_A100_v4` (or chosen A100 size)
- [ ] Request exemption for **Resource Group**: `rg-apim-mcp-aks-kaito`
- [ ] Request exemption for **Subscription**: Current MCAPS subscription ID
- [ ] **Justification**: "AI/ML model inference using Azure Kaito framework for production AI agents"

**Expected Timeline**: 1-3 business days (varies by organization)

---

#### 3.2 Quota Verification
**Action Items**:
- [ ] Check current A100 quota in subscription:
  ```powershell
  az vm list-usage --location eastus --output table | Select-String "NC"
  ```
- [ ] If needed, request quota increase:
  - Portal: Support → New support request → Service and subscription limits (quotas)
  - Request: **NCadsA100v4 Family vCPUs** (24 vCPUs for 1x Standard_NC24ads_A100_v4)
  - Region: Your target region (eastus, eastus2, etc.)

**Expected Timeline**: 1-5 business days

---

### 4. Deployment Scripts

#### 4.1 `scripts/install-kaito.sh`
**Current State**: Ready to use, no changes needed
**Verification Needed**: Ensure script installs latest Kaito version supporting A100

```bash
#!/bin/bash
# No changes required - script is GPU-agnostic
# Kaito operator will automatically handle A100 GPUs
```

**Action Items**:
- [ ] No changes required
- [ ] Run after GPU node pool is created

---

#### 4.2 `scripts/install-kaito.ps1`
**Current State**: May need to be created (check if exists)

**Action Items**:
- [ ] Check if PowerShell version exists
- [ ] If not, create PowerShell equivalent of install-kaito.sh:

```powershell
# scripts/install-kaito.ps1
# Install Kaito operator on AKS cluster

Write-Host "🚀 Installing Kaito operator on AKS..." -ForegroundColor Green

# Check if kubectl is available
if (-not (Get-Command kubectl -ErrorAction SilentlyContinue)) {
    Write-Host "❌ kubectl not found. Please install kubectl first." -ForegroundColor Red
    exit 1
}

# Check if helm is available
if (-not (Get-Command helm -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Helm not found. Please install Helm first." -ForegroundColor Red
    exit 1
}

# Add Kaito Helm repository
Write-Host "📦 Adding Kaito Helm repository..." -ForegroundColor Cyan
helm repo add kaito https://azure.github.io/kaito
helm repo update

# Install Kaito workspace CRDs
Write-Host "📋 Installing Kaito CRDs..." -ForegroundColor Cyan
kubectl apply -f https://raw.githubusercontent.com/kaito-project/kaito/main/charts/kaito/workspace/crds/kaito.sh_workspaces.yaml

# Install Kaito operator
Write-Host "⚙️  Installing Kaito operator..." -ForegroundColor Cyan
helm upgrade --install kaito kaito/kaito `
    --namespace kaito-system `
    --create-namespace `
    --set image.repository=mcr.microsoft.com/aks/kaito/workspace `
    --wait

Write-Host "✅ Kaito operator installed successfully!" -ForegroundColor Green

# Verify installation
Write-Host "🔍 Verifying Kaito installation..." -ForegroundColor Cyan
kubectl get pods -n kaito-system

Write-Host ""
Write-Host "✅ Kaito is ready!" -ForegroundColor Green
Write-Host "📝 You can now apply Kaito Workspace CRDs to deploy models." -ForegroundColor Yellow
```

---

### 5. Documentation Updates

#### 5.1 `README.md`
**Required Updates**: Add A100-specific deployment instructions

**Action Items**:
- [ ] Add section: "A100 GPU Deployment"
- [ ] Document policy exemption requirement
- [ ] Add quota verification steps
- [ ] Update model size recommendations for A100

---

#### 5.2 `docs/DEPLOYMENT_NOTES.md`
**Required Updates**: Update GPU configuration notes

**Action Items**:
- [ ] Update "GPU Node Pool Status" section
- [ ] Document A100 VM size change
- [ ] Add policy exemption completion date
- [ ] Document actual GPU node count deployed

---

#### 5.3 `docs/ARCHITECTURE.md`
**Required Updates**: Update diagrams and component descriptions

**Action Items**:
- [ ] Update GPU Node Pool component to reflect A100
- [ ] Update resource specifications in diagrams
- [ ] Add A100-specific model capabilities

---

### 6. Testing & Validation

#### 6.1 New Test: `tests/test_a100_gpu.py`
**Purpose**: Validate A100 GPU availability and Kaito deployment

**Action Items**:
- [ ] Create new test file to verify:
  - GPU node pool exists
  - Nodes have A100 GPU labels
  - Kaito operator is running
  - Kaito workspace can schedule on A100 nodes
  - Model inference works

**Proposed Test Structure**:
```python
"""
Test A100 GPU Node Pool and Kaito Deployment
"""
import subprocess
import json

def test_gpu_node_pool_exists():
    """Verify GPU node pool with A100 exists"""
    result = subprocess.run(
        ["kubectl", "get", "nodes", "-l", "kaito=true", "-o", "json"],
        capture_output=True, text=True
    )
    nodes = json.loads(result.stdout)
    assert len(nodes["items"]) >= 1, "No GPU nodes found"
    
    # Verify A100 GPU
    for node in nodes["items"]:
        gpu_count = node["status"]["capacity"].get("nvidia.com/gpu", "0")
        assert int(gpu_count) >= 1, f"Node has no GPUs"

def test_kaito_operator_running():
    """Verify Kaito operator is deployed and healthy"""
    result = subprocess.run(
        ["kubectl", "get", "pods", "-n", "kaito-system", "-o", "json"],
        capture_output=True, text=True
    )
    pods = json.loads(result.stdout)
    assert len(pods["items"]) >= 1, "Kaito operator not found"
    
    for pod in pods["items"]:
        status = pod["status"]["phase"]
        assert status == "Running", f"Kaito pod not running: {status}"

def test_kaito_workspace_deployment():
    """Verify Kaito workspace can be deployed"""
    result = subprocess.run(
        ["kubectl", "get", "workspace", "-o", "json"],
        capture_output=True, text=True
    )
    workspaces = json.loads(result.stdout)
    assert len(workspaces["items"]) >= 1, "No Kaito workspaces found"
```

---

#### 6.2 Update: `tests/test_apim_mcp_aks.py`
**Required Updates**: Add GPU node validation

**Action Items**:
- [ ] Add test case: `test_gpu_node_pool_ready()`
- [ ] Add test case: `test_kaito_operator_healthy()`
- [ ] Add test case: `test_model_inference_endpoint()`

---

### 7. Cost Considerations

#### 7.1 Estimated Costs (East US 2 region)

| Component | Specification | Estimated Cost/Month |
|-----------|--------------|---------------------|
| **AKS System Nodes** | 2x Standard_DS2_v2 | ~$140 |
| **A100 GPU Node (minimum)** | 1x Standard_NC24ads_A100_v4 | ~$3,285 |
| **A100 GPU Node (max autoscale)** | 4x Standard_NC24ads_A100_v4 | ~$13,140 |
| **Container Registry** | Standard | ~$20 |
| **Storage Account** | Standard LRS | ~$25 |
| **APIM** | BasicV2 | ~$240 |
| **Other Services** | Monitoring, VNet, etc. | ~$50 |
| **TOTAL (min config)** | 1 GPU node running | **~$3,760/month** |
| **TOTAL (max autoscale)** | 4 GPU nodes running | **~$13,620/month** |

**Cost Optimization Recommendations**:
- [ ] Start with `gpuNodePoolMinCount: 0` and `gpuNodePoolMaxCount: 1` for development
- [ ] Enable autoscaling based on workload demand
- [ ] Use Azure Reserved Instances for 1-3 year commit (30-60% discount)
- [ ] Consider spot instances for non-production workloads (up to 90% discount)
- [ ] Set up cost alerts in Azure Cost Management

---

## Deployment Sequence

### Phase 1: Pre-Deployment (1-3 business days)
1. [ ] Submit Azure Policy exemption request for A100 VMs
2. [ ] Verify A100 quota in subscription
3. [ ] Request quota increase if needed
4. [ ] Review and approve budget for GPU nodes

### Phase 2: Infrastructure Updates (30 minutes)
1. [ ] Update `infra/main.bicep` with A100 configuration
2. [ ] Update `infra/core/aks/aks-cluster.bicep` defaults
3. [ ] Commit changes to git repository
4. [ ] Run `azd up` to update infrastructure

### Phase 3: Verify GPU Node Pool (10 minutes)
1. [ ] Verify GPU node pool creation:
   ```powershell
   kubectl get nodes -l kaito=true
   kubectl describe node <gpu-node-name> | Select-String "nvidia"
   ```
2. [ ] Verify GPU resources:
   ```powershell
   kubectl get nodes -o json | jq '.items[].status.capacity | select(."nvidia.com/gpu" != null)'
   ```

### Phase 4: Install Kaito (15 minutes)
1. [ ] Get AKS credentials:
   ```powershell
   az aks get-credentials --resource-group rg-apim-mcp-aks-kaito --name aks-jozz4mn7tla5s
   ```
2. [ ] Run Kaito installation:
   ```powershell
   .\scripts\install-kaito.ps1
   ```
3. [ ] Verify Kaito operator:
   ```powershell
   kubectl get pods -n kaito-system
   ```

### Phase 5: Deploy Model (20 minutes)
1. [ ] Update `k8s/kaito-foundry-workspace.yaml` with A100 configuration
2. [ ] Apply Kaito workspace:
   ```powershell
   kubectl apply -f k8s/kaito-foundry-workspace.yaml
   ```
3. [ ] Monitor workspace status:
   ```powershell
   kubectl get workspace -w
   ```
4. [ ] Verify model pod is running:
   ```powershell
   kubectl get pods -l kaito-workspace=azure-foundry-model
   ```

### Phase 6: Testing & Validation (30 minutes)
1. [ ] Run infrastructure tests:
   ```powershell
   python tests/test_apim_mcp_aks.py
   ```
2. [ ] Run A100-specific tests:
   ```powershell
   python tests/test_a100_gpu.py
   ```
3. [ ] Test model inference endpoint
4. [ ] Test MCP tool integration with model

### Phase 7: Documentation (15 minutes)
1. [ ] Update `docs/DEPLOYMENT_NOTES.md` with deployment date and configuration
2. [ ] Update `README.md` with A100 deployment status
3. [ ] Document model endpoint URL and access instructions

---

## Rollback Plan

If deployment fails or costs exceed budget:

### Immediate Rollback (5 minutes)
```powershell
# Disable GPU node pool without destroying infrastructure
az aks nodepool scale --resource-group rg-apim-mcp-aks-kaito --cluster-name aks-jozz4mn7tla5s --name gpupool --node-count 0
```

### Full Rollback (15 minutes)
1. [ ] Update `infra/main.bicep`: Set `enableGpuNodePool: false`
2. [ ] Run `azd up` to remove GPU node pool
3. [ ] Delete Kaito workspaces:
   ```powershell
   kubectl delete workspace --all
   ```
4. [ ] Optionally uninstall Kaito operator:
   ```powershell
   helm uninstall kaito -n kaito-system
   ```

---

## Summary Checklist

### Infrastructure (Bicep)
- [ ] Update `infra/main.bicep` - Change GPU VM size to A100
- [ ] Update `infra/main.bicep` - Set `enableGpuNodePool: true`
- [ ] Update `infra/main.bicep` - Set `gpuNodePoolMinCount: 1`
- [ ] Update `infra/core/aks/aks-cluster.bicep` - Update defaults

### Kubernetes Manifests
- [ ] Update `k8s/kaito-workspace.yaml` - A100 VM size
- [ ] Update `k8s/kaito-foundry-workspace.yaml` - A100 VM size
- [ ] Update `k8s/kaito-foundry-workspace.yaml` - Model selection

### Azure Policy & Permissions
- [ ] Submit policy exemption for A100 VMs
- [ ] Verify A100 quota availability
- [ ] Request quota increase if needed

### Deployment & Testing
- [ ] Run `azd up` to update infrastructure
- [ ] Install Kaito operator
- [ ] Deploy Kaito workspace with model
- [ ] Create and run A100 validation tests
- [ ] Verify model inference works

### Documentation
- [ ] Update `README.md`
- [ ] Update `docs/DEPLOYMENT_NOTES.md`
- [ ] Update `docs/ARCHITECTURE.md`
- [ ] Create `tests/test_a100_gpu.py`

### Cost Management
- [ ] Set up Azure Cost Management alerts
- [ ] Configure autoscaling thresholds
- [ ] Review monthly budget allocation

---

## Next Steps

1. **Review this plan** with stakeholders and get approval for GPU costs
2. **Submit policy exemption** request (longest lead time)
3. **Make code changes** in parallel while waiting for policy exemption
4. **Test in development** environment if available
5. **Execute deployment** once policy exemption is approved

---

## Support Resources

- **Azure Policy**: https://aka.ms/AzPolicyWiki
- **Kaito Documentation**: https://github.com/kaito-project/kaito
- **Azure A100 VMs**: https://learn.microsoft.com/azure/virtual-machines/nca100-v4-series
- **Azure Foundry**: https://learn.microsoft.com/azure/ai-studio/
- **AKS GPU Best Practices**: https://learn.microsoft.com/azure/aks/gpu-cluster

---

**Document Version**: 1.0  
**Created**: October 22, 2025  
**Last Updated**: October 22, 2025  
**Owner**: Infrastructure Team
