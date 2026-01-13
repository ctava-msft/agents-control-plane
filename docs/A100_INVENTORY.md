# A100 GPU Deployment - Complete Inventory

**Date Created**: October 22, 2025  
**Resource Group**: `rg-apim-mcp-aks-kaito`  
**Current State**: T4 GPU (disabled)  
**Target State**: A100 GPU (enabled)

---

## Executive Summary

To deploy language models to an A100 GPU node pool in your AKS cluster, you need to:

1. **Update 4 files** (15 lines of code)
2. **Get Azure Policy exemption** (1-3 business days)
3. **Verify GPU quota** (immediate or 1-5 days)
4. **Deploy with `azd up`** (30 minutes)

**Cost Impact**: +$2,915/month for 1 A100 node (vs current T4 estimate)

---

## Files Inventory

### Files Requiring Changes

| File | Lines | Changes | Priority | Complexity |
|------|-------|---------|----------|------------|
| `infra/main.bicep` | 150-156 | 4 params | **CRITICAL** | Easy |
| `infra/core/aks/aks-cluster.bicep` | 19-26 | 3 defaults | Recommended | Easy |
| `k8s/kaito-workspace.yaml` | 11, 20 | VM + model | **CRITICAL** | Easy |
| `k8s/kaito-foundry-workspace.yaml` | 15, 30 | VM + model | **CRITICAL** | Easy |

### Files NOT Requiring Changes

- ✅ `scripts/install-kaito.sh` - GPU-agnostic
- ✅ `scripts/install-kaito.ps1` - Will be created if missing
- ✅ `infra/main.parameters.json` - Uses defaults
- ✅ `src/mcp_server.py` - No changes needed
- ✅ `k8s/mcp-server-*.yaml` - Runs on system nodes
- ✅ `tests/test_apim_mcp_aks.py` - Will add GPU tests later

### Documentation to Update

| File | Section | Update |
|------|---------|--------|
| `README.md` | Prerequisites | Add A100 requirements |
| `docs/DEPLOYMENT_NOTES.md` | GPU Node Pool Status | Update to A100 |
| `docs/ARCHITECTURE.md` | Component Diagram | Update GPU specs |

---

## Detailed Change Inventory

### 1. Infrastructure (Bicep)

#### `infra/main.bicep` - 4 Changes
```diff
  module aksCluster './core/aks/aks-cluster.bicep' = {
    params: {
-     gpuNodePoolVmSize: 'Standard_NC4as_T4_v3'
+     gpuNodePoolVmSize: 'Standard_NC24ads_A100_v4'
      
-     gpuNodePoolMinCount: 0
+     gpuNodePoolMinCount: 1
      
-     gpuNodePoolMaxCount: 3
+     gpuNodePoolMaxCount: 4
      
-     enableGpuNodePool: false
+     enableGpuNodePool: true
    }
  }
```

#### `infra/core/aks/aks-cluster.bicep` - 3 Changes
```diff
- param gpuNodePoolVmSize string = 'Standard_NC4as_T4_v3'
+ param gpuNodePoolVmSize string = 'Standard_NC24ads_A100_v4'

- param gpuNodePoolMinCount int = 0
+ param gpuNodePoolMinCount int = 1

- param gpuNodePoolMaxCount int = 3
+ param gpuNodePoolMaxCount int = 4
```

### 2. Kubernetes Manifests

#### `k8s/kaito-workspace.yaml` - 1-2 Changes
```diff
  spec:
    inference:
      preset:
-       name: phi-3-mini-4k-instruct
+       name: phi-3-medium-128k-instruct  # OPTIONAL
    
    resource:
-     instanceType: Standard_NC6s_v3
+     instanceType: Standard_NC24ads_A100_v4
```

#### `k8s/kaito-foundry-workspace.yaml` - 1-2 Changes
```diff
  spec:
    inference:
      preset:
-       name: phi-3-mini-4k-instruct
+       name: llama-2-7b-chat  # OPTIONAL
    
    resource:
-     instanceType: Standard_NC6s_v3
+     instanceType: Standard_NC24ads_A100_v4
```

### 3. Scripts

#### `scripts/apply-a100-changes.ps1` - NEW FILE
- **Status**: Created ✅
- **Purpose**: Automate all code changes
- **Usage**: `.\scripts\apply-a100-changes.ps1 [-DryRun] [-UpgradeModels]`

### 4. Documentation

#### New Documentation Files Created

1. **`docs/A100_GPU_DEPLOYMENT_PLAN.md`** ✅
   - Complete deployment plan
   - VM size options
   - Cost estimates
   - Step-by-step instructions
   - Rollback procedures
   - 47 sections, comprehensive guide

2. **`docs/A100_CHANGES_SUMMARY.md`** ✅
   - Quick reference
   - Critical files to change
   - VM comparison table
   - Deployment commands
   - Cost estimates
   - Rollback command

3. **`docs/A100_CODE_DIFF.md`** ✅
   - Line-by-line diffs
   - Before/after code blocks
   - Verification commands
   - Automated script
   - Complete change list

4. **`docs/A100_INVENTORY.md`** ✅
   - This file
   - Complete change inventory
   - Resource requirements
   - Deployment checklist

---

## Resource Requirements

### Azure Resources

| Resource | Current | Target | Change |
|----------|---------|--------|--------|
| **AKS System Nodes** | 2x Standard_DS2_v2 | Same | None |
| **GPU Nodes** | None (disabled) | 1-4x A100 | NEW |
| **GPU Type** | T4 (16GB) | A100 (40GB) | +150% memory |
| **vCPUs per GPU node** | 4 | 24 | +500% |
| **RAM per GPU node** | 28 GB | 220 GB | +685% |
| **GPU Compute** | 8.1 TFLOPS | 312 TFLOPS | +3,750% |

### Azure Policy

**Current Status**: ❌ **BLOCKED**
- Policy blocks `Standard_NC4as_T4_v3` in MCAPS subscription
- Same policy will likely block A100 sizes

**Required Action**: Submit exemption request
- **URL**: https://aka.ms/AzPolicyWiki
- **Scope**: Resource Group `rg-apim-mcp-aks-kaito`
- **SKUs**: `Standard_NC24ads_A100_v4` (or other A100 sizes)
- **Timeline**: 1-3 business days

### Quota

**Required vCPU Quota**: 
- **NCadsA100v4 Family vCPUs**
- **Amount**: 24 vCPUs (for 1 node) to 96 vCPUs (for 4 nodes)
- **Region**: Your deployment region (e.g., eastus, eastus2)

**Check Current Quota**:
```powershell
az vm list-usage --location eastus --output table | Select-String "NCadsA100"
```

**Request Quota Increase**:
- Portal: Support → Service and subscription limits → NCadsA100v4 Family vCPUs
- Timeline: 1-5 business days

---

## Cost Analysis

### Monthly Cost Breakdown

| Component | Current | With 1 A100 | With 4 A100 (max) | Δ from Current |
|-----------|---------|-------------|-------------------|----------------|
| System Nodes (2x DS2_v2) | $140 | $140 | $140 | - |
| GPU Nodes | $0 | $3,285 | $13,140 | +$3,285 to +$13,140 |
| Container Registry | $20 | $20 | $20 | - |
| Storage | $25 | $25 | $25 | - |
| APIM BasicV2 | $240 | $240 | $240 | - |
| Monitoring & Network | $50 | $50 | $50 | - |
| **TOTAL** | **$475** | **$3,760** | **$13,620** | **+692% to +2,767%** |

### Cost Optimization

1. **Development Configuration** (Recommended for testing):
   ```bicep
   gpuNodePoolMinCount: 0  // Scale to zero when not in use
   gpuNodePoolMaxCount: 1  // Limit to 1 node
   ```
   **Cost**: $475/month (same as current) when scaled to zero

2. **Production Configuration** (Current plan):
   ```bicep
   gpuNodePoolMinCount: 1  // Always 1 node running
   gpuNodePoolMaxCount: 4  // Scale up to 4 nodes
   ```
   **Cost**: $3,760/month minimum, up to $13,620/month peak

3. **Reserved Instances** (1-3 year commitment):
   - **1 Year**: 30% discount → $2,300/month per node
   - **3 Year**: 60% discount → $1,314/month per node

4. **Spot Instances** (non-production):
   - **Discount**: Up to 90% off
   - **Cost**: ~$328/month per node
   - **Risk**: Can be evicted with 30-second notice

### Budget Recommendations

| Environment | Configuration | Monthly Budget | Annual Budget |
|-------------|--------------|----------------|---------------|
| **Development** | 0-1 nodes, autoscale | $500 - $4,000 | $6K - $48K |
| **Staging** | 1-2 nodes, autoscale | $4,000 - $7,000 | $48K - $84K |
| **Production** | 1-4 nodes, reserved | $3,000 - $8,000 | $36K - $96K |

---

## Deployment Checklist

### Pre-Deployment (Complete BEFORE making changes)

- [ ] **Budget Approval**
  - [ ] Stakeholder approval for $3,760-$13,620/month
  - [ ] Cost alerts configured in Azure Cost Management
  
- [ ] **Azure Policy Exemption**
  - [ ] Request submitted to https://aka.ms/AzPolicyWiki
  - [ ] Exemption approved for A100 VMs
  - [ ] Confirmation email received
  
- [ ] **Quota Verification**
  - [ ] Current NCadsA100v4 quota checked
  - [ ] Quota increase requested (if needed)
  - [ ] Quota increase approved
  
- [ ] **Regional Availability**
  - [ ] Confirmed A100 VMs available in target region
  - [ ] Confirmed Kaito supports target region

### Code Changes

- [ ] **Backup Current Code**
  - [ ] Git commit current state
  - [ ] Tag current version: `git tag v1.0-t4-gpu`
  
- [ ] **Apply Changes** (Choose ONE method)
  
  **Method 1: Automated Script** (Recommended)
  - [ ] Run: `.\scripts\apply-a100-changes.ps1 -DryRun` (preview)
  - [ ] Run: `.\scripts\apply-a100-changes.ps1` (apply)
  - [ ] Optional: Add `-UpgradeModels` flag for larger models
  
  **Method 2: Manual Edits**
  - [ ] Edit `infra/main.bicep` (4 changes)
  - [ ] Edit `infra/core/aks/aks-cluster.bicep` (3 changes)
  - [ ] Edit `k8s/kaito-workspace.yaml` (1 change)
  - [ ] Edit `k8s/kaito-foundry-workspace.yaml` (1 change)
  
- [ ] **Verify Changes**
  - [ ] Run: `git diff` (review all changes)
  - [ ] Verify A100 VM sizes: `Select-String -Path "infra\*.bicep" -Pattern "NC24ads_A100"`
  - [ ] Verify GPU enabled: `Select-String -Path "infra\main.bicep" -Pattern "enableGpuNodePool: true"`
  
- [ ] **Commit Changes**
  - [ ] Commit to git: `git commit -am "feat: migrate to A100 GPUs"`
  - [ ] Tag new version: `git tag v2.0-a100-gpu`

### Deployment

- [ ] **Deploy Infrastructure**
  - [ ] Run: `azd up`
  - [ ] Monitor for errors
  - [ ] Verify deployment success
  
- [ ] **Verify AKS Cluster**
  - [ ] Get credentials: `az aks get-credentials --resource-group rg-apim-mcp-aks-kaito --name aks-jozz4mn7tla5s`
  - [ ] Check nodes: `kubectl get nodes`
  - [ ] Verify GPU nodes exist: `kubectl get nodes -l kaito=true`
  - [ ] Check GPU resources: `kubectl describe node <gpu-node> | Select-String "nvidia"`
  
- [ ] **Install Kaito**
  - [ ] Run: `.\scripts\install-kaito.ps1`
  - [ ] Verify operator: `kubectl get pods -n kaito-system`
  - [ ] Check CRDs: `kubectl get crd | Select-String "kaito"`
  
- [ ] **Deploy Model**
  - [ ] Apply workspace: `kubectl apply -f k8s/kaito-foundry-workspace.yaml`
  - [ ] Monitor workspace: `kubectl get workspace -w`
  - [ ] Wait for ready state (5-15 minutes for model download)
  - [ ] Verify model pod: `kubectl get pods -l kaito-workspace=azure-foundry-model`

### Testing & Validation

- [ ] **Infrastructure Tests**
  - [ ] Run: `python tests/test_apim_mcp_aks.py`
  - [ ] Verify: All tests pass
  
- [ ] **GPU Tests** (New tests to create)
  - [ ] Create: `tests/test_a100_gpu.py`
  - [ ] Test: GPU node pool exists
  - [ ] Test: Kaito operator running
  - [ ] Test: Workspace deployed
  - [ ] Test: Model pod running
  
- [ ] **Model Inference Tests**
  - [ ] Port-forward to model: `kubectl port-forward svc/azure-foundry-model 8080:80`
  - [ ] Test inference endpoint
  - [ ] Verify response quality
  
- [ ] **Integration Tests**
  - [ ] Test MCP tools can access model
  - [ ] Test APIM → MCP → Model flow
  - [ ] Verify end-to-end AI agent integration

### Documentation

- [ ] **Update README.md**
  - [ ] Add A100 GPU section
  - [ ] Update prerequisites
  - [ ] Add cost warnings
  
- [ ] **Update DEPLOYMENT_NOTES.md**
  - [ ] Change GPU status from "DISABLED" to "ENABLED"
  - [ ] Update VM size to A100
  - [ ] Add deployment date
  - [ ] Document actual node count
  
- [ ] **Update ARCHITECTURE.md**
  - [ ] Update GPU node pool diagram
  - [ ] Update resource specifications
  - [ ] Add A100 capabilities

### Monitoring & Operations

- [ ] **Configure Monitoring**
  - [ ] Set up GPU utilization alerts
  - [ ] Configure cost alerts
  - [ ] Enable autoscaling metrics
  
- [ ] **Create Runbooks**
  - [ ] Document scale-up procedure
  - [ ] Document scale-down procedure
  - [ ] Document rollback procedure
  
- [ ] **Establish SLAs**
  - [ ] Define model inference latency targets
  - [ ] Define availability targets
  - [ ] Define cost optimization targets

---

## Rollback Procedures

### Quick Scale-Down (No infrastructure changes)
```powershell
# Scale GPU node pool to zero
az aks nodepool scale `
  --resource-group rg-apim-mcp-aks-kaito `
  --cluster-name aks-jozz4mn7tla5s `
  --name gpupool `
  --node-count 0

# Saves ~$3,285/month immediately
```

### Full Rollback to T4 Configuration
```powershell
# 1. Revert code changes
git checkout v1.0-t4-gpu

# 2. Redeploy infrastructure
azd up

# 3. Delete Kaito workspaces
kubectl delete workspace --all

# 4. Optional: Uninstall Kaito
helm uninstall kaito -n kaito-system
```

### Emergency Stop (Nuclear option)
```powershell
# Delete GPU node pool entirely
az aks nodepool delete `
  --resource-group rg-apim-mcp-aks-kaito `
  --cluster-name aks-jozz4mn7tla5s `
  --name gpupool `
  --no-wait

# Stops ALL GPU costs immediately
```

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| **Policy exemption denied** | Medium | High | Pre-approve with MCAPS team |
| **Quota unavailable** | Low | High | Request quota early |
| **Cost overrun** | Medium | High | Set Azure cost alerts, use autoscaling |
| **Model doesn't fit in memory** | Low | Medium | Start with smaller models |
| **Performance not as expected** | Low | Medium | Benchmark before production |
| **Downtime during migration** | Low | Low | MCP server runs on system nodes |

---

## Success Criteria

### Functional
- [ ] GPU node pool created with A100 VMs
- [ ] Kaito operator installed and healthy
- [ ] Language model deployed and responding
- [ ] MCP tools can access model endpoints
- [ ] End-to-end AI agent integration works
- [ ] All tests pass (11/11 infrastructure + new GPU tests)

### Performance
- [ ] Model inference latency < 500ms (p95)
- [ ] GPU utilization > 60% during inference
- [ ] No GPU memory errors
- [ ] Autoscaling responds within 5 minutes

### Cost
- [ ] Monthly spend within approved budget
- [ ] Cost alerts configured and tested
- [ ] Autoscaling prevents unnecessary scaling
- [ ] Reserved instances evaluated for 3-month usage

### Operational
- [ ] Documentation complete and accurate
- [ ] Runbooks created for common operations
- [ ] Monitoring and alerting functional
- [ ] Team trained on GPU operations

---

## Timeline

| Phase | Duration | Dependencies | Owner |
|-------|----------|--------------|-------|
| **Pre-Approval** | 1-3 days | Budget approval | Product Owner |
| **Policy Exemption** | 1-3 days | MCAPS approval | DevOps Team |
| **Quota Request** | 0-5 days | Azure support | DevOps Team |
| **Code Changes** | 1 hour | Policy exemption | Developer |
| **Deployment** | 30 minutes | Code changes | DevOps Team |
| **Kaito Install** | 15 minutes | Deployment | DevOps Team |
| **Model Deployment** | 15 minutes | Kaito install | DevOps Team |
| **Testing** | 2-4 hours | Model deployment | QA Team |
| **Documentation** | 1 hour | Testing | Technical Writer |
| **TOTAL** | **2-11 days** | All above | Team |

**Critical Path**: Policy exemption + quota request (1-8 days)

---

## Support & Resources

### Internal Resources
- **This Repository**: All documentation and scripts
- **Backup Directory**: Created by apply script with timestamp
- **Git Tags**: `v1.0-t4-gpu` (before), `v2.0-a100-gpu` (after)

### Azure Resources
- **Policy Exemption**: https://aka.ms/AzPolicyWiki
- **Quota Requests**: Azure Portal → Support → Service and subscription limits
- **A100 VM Docs**: https://learn.microsoft.com/azure/virtual-machines/nca100-v4-series
- **AKS GPU Docs**: https://learn.microsoft.com/azure/aks/gpu-cluster

### Kaito Resources
- **GitHub**: https://github.com/kaito-project/kaito
- **Docs**: https://github.com/kaito-project/kaito/tree/main/docs
- **Supported Models**: https://github.com/kaito-project/kaito/blob/main/presets/README.md

### Azure Foundry
- **AI Studio**: https://ai.azure.com
- **Model Catalog**: https://learn.microsoft.com/azure/ai-studio/how-to/model-catalog
- **Deployment Guide**: https://learn.microsoft.com/azure/ai-studio/how-to/deploy-models

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-10-22 | AI Assistant | Initial comprehensive inventory |

---

## Appendix: Quick Command Reference

### Deployment
```powershell
# Apply code changes
.\scripts\apply-a100-changes.ps1

# Deploy infrastructure
azd up

# Get AKS credentials
az aks get-credentials --resource-group rg-apim-mcp-aks-kaito --name aks-jozz4mn7tla5s

# Install Kaito
.\scripts\install-kaito.ps1

# Deploy model
kubectl apply -f k8s/kaito-foundry-workspace.yaml
```

### Verification
```powershell
# Check GPU nodes
kubectl get nodes -l kaito=true

# Check Kaito operator
kubectl get pods -n kaito-system

# Check workspace
kubectl get workspace

# Check model pod
kubectl get pods -l kaito-workspace=azure-foundry-model

# Check GPU usage
kubectl top nodes
```

### Monitoring
```powershell
# Watch workspace deployment
kubectl get workspace -w

# View model pod logs
kubectl logs -l kaito-workspace=azure-foundry-model

# Describe node (GPU info)
kubectl describe node <gpu-node-name>
```

### Troubleshooting
```powershell
# Check node events
kubectl get events --sort-by='.lastTimestamp'

# Check workspace status
kubectl describe workspace azure-foundry-model

# Check pod status
kubectl describe pod <model-pod-name>

# View operator logs
kubectl logs -n kaito-system -l app=kaito
```

---

**END OF INVENTORY**

For detailed instructions, see:
- **Full Plan**: [A100_GPU_DEPLOYMENT_PLAN.md](./A100_GPU_DEPLOYMENT_PLAN.md)
- **Quick Reference**: [A100_CHANGES_SUMMARY.md](./A100_CHANGES_SUMMARY.md)
- **Code Diff**: [A100_CODE_DIFF.md](./A100_CODE_DIFF.md)
