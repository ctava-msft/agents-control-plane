# A100 GPU Deployment - Quick Reference

## Critical Files to Change

### 1. `infra/main.bicep` (Lines 150-156)
```bicep
gpuNodePoolVmSize: 'Standard_NC24ads_A100_v4'  // Change from Standard_NC4as_T4_v3
gpuNodePoolMinCount: 1                          // Change from 0
gpuNodePoolMaxCount: 4                          // Change from 3
enableGpuNodePool: true                         // Change from false
```

### 2. `infra/core/aks/aks-cluster.bicep` (Lines 19-26, 43-44)
```bicep
param gpuNodePoolVmSize string = 'Standard_NC24ads_A100_v4'  // Change default
param gpuNodePoolMinCount int = 1                             // Change default
param gpuNodePoolMaxCount int = 4                             // Change default
param enableGpuNodePool bool = true                           // Optional: change default
```

### 3. `k8s/kaito-workspace.yaml` (Lines 8, 17)
```yaml
name: phi-3-medium-128k-instruct      # Upgrade model
instanceType: Standard_NC24ads_A100_v4  # Change from Standard_NC6s_v3
```

### 4. `k8s/kaito-foundry-workspace.yaml` (Lines 14, 27)
```yaml
name: llama-2-7b-chat                 # Upgrade model
instanceType: Standard_NC24ads_A100_v4  # Change from Standard_NC6s_v3
```

---

## VM Size Comparison

| Aspect | Current (T4) | Proposed (A100) |
|--------|-------------|-----------------|
| **VM Size** | Standard_NC4as_T4_v3 | Standard_NC24ads_A100_v4 |
| **GPU** | 1x NVIDIA T4 (16GB) | 1x NVIDIA A100 (40GB) |
| **vCPUs** | 4 | 24 |
| **RAM** | 28 GB | 220 GB |
| **GPU Memory** | 16 GB | 40 GB |
| **Cost/Month** | ~$370 | ~$3,285 |
| **Performance** | Baseline | ~10x faster |

---

## Pre-Deployment Requirements

### 1. Azure Policy Exemption (CRITICAL)
- **URL**: https://aka.ms/AzPolicyWiki
- **Request**: Exemption for `Standard_NC24ads_A100_v4` in `rg-apim-mcp-aks-kaito`
- **Timeline**: 1-3 business days

### 2. Quota Check
```powershell
az vm list-usage --location eastus --output table | Select-String "NCadsA100"
```
- **Required**: 24 vCPUs (for 1 node)
- **Request if needed**: Via Azure Portal Support

---

## Deployment Commands

### Step 1: Update Infrastructure
```powershell
# Make code changes above, then:
azd up
```

### Step 2: Verify GPU Nodes
```powershell
kubectl get nodes -l kaito=true
kubectl describe node <gpu-node-name> | Select-String "nvidia"
```

### Step 3: Install Kaito
```powershell
.\scripts\install-kaito.ps1
```

### Step 4: Deploy Model
```powershell
kubectl apply -f k8s/kaito-foundry-workspace.yaml
kubectl get workspace -w
```

### Step 5: Verify
```powershell
kubectl get pods -l kaito-workspace=azure-foundry-model
```

---

## Cost Estimate

| Configuration | Monthly Cost |
|--------------|-------------|
| **Development** (0-1 GPU node, autoscale) | $3,760 |
| **Production** (1-4 GPU nodes, autoscale) | $3,760 - $13,620 |

💡 **Tip**: Start with `minCount: 0` for dev to save costs when not in use.

---

## Rollback Command

If you need to quickly scale down:
```powershell
az aks nodepool scale --resource-group rg-apim-mcp-aks-kaito --cluster-name aks-jozz4mn7tla5s --name gpupool --node-count 0
```

---

## Model Recommendations for A100

| Model | Context | GPU Memory | Use Case |
|-------|---------|------------|----------|
| **Phi-3-Mini-128K** | 128K tokens | ~8 GB | Long context, fast inference |
| **Phi-3-Medium** | 128K tokens | ~16 GB | Better quality, long context |
| **Llama-2-7B** | 4K tokens | ~14 GB | General purpose, high quality |
| **Mistral-7B** | 32K tokens | ~14 GB | Long context, instruction following |
| **Llama-2-13B** | 4K tokens | ~26 GB | Higher quality, more capable |

A100 40GB can handle any of these models with room for batch processing.

---

## Testing Checklist

After deployment:
- [ ] GPU nodes are running: `kubectl get nodes -l kaito=true`
- [ ] Kaito operator is healthy: `kubectl get pods -n kaito-system`
- [ ] Workspace is ready: `kubectl get workspace`
- [ ] Model pod is running: `kubectl get pods -l kaito-workspace=azure-foundry-model`
- [ ] Tests pass: `python tests/test_apim_mcp_aks.py`
- [ ] Model inference works: Test via MCP tools

---

## Troubleshooting

### Policy Error
```
Error: RequestDisallowedByPolicy
```
**Solution**: Submit policy exemption request at https://aka.ms/AzPolicyWiki

### Quota Error
```
Error: Operation could not be completed as it results in exceeding approved quota
```
**Solution**: Request quota increase via Azure Portal Support

### Node Not Scheduling
```
kubectl describe pod <model-pod>
```
Look for: `0/X nodes available: insufficient nvidia.com/gpu`
**Solution**: Verify GPU node pool is running and has correct labels

---

**For full details, see**: [A100_GPU_DEPLOYMENT_PLAN.md](./A100_GPU_DEPLOYMENT_PLAN.md)
