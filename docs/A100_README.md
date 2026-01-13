# A100 GPU Deployment Documentation

**Complete documentation for migrating from T4 to A100 GPUs**

---

## 📚 Documentation Index

### 🎯 Start Here
- **[Quick Changes Summary](./A100_CHANGES_SUMMARY.md)** - 2-minute overview of what needs to change
- **[Complete Inventory](./A100_INVENTORY.md)** - Exhaustive checklist and resource requirements

### 📖 Detailed Guides
- **[Full Deployment Plan](./A100_GPU_DEPLOYMENT_PLAN.md)** - Step-by-step deployment guide (47 sections)
- **[Code Changes Diff](./A100_CODE_DIFF.md)** - Exact line-by-line code changes

### 🔧 Automation
- **[Automated Script](../scripts/apply-a100-changes.ps1)** - PowerShell script to apply all changes

---

## 🚀 Quick Start

### Option 1: Automated (Recommended)
```powershell
# Preview changes
.\scripts\apply-a100-changes.ps1 -DryRun

# Apply changes
.\scripts\apply-a100-changes.ps1

# Optional: Upgrade to larger models
.\scripts\apply-a100-changes.ps1 -UpgradeModels
```

### Option 2: Manual
See [Code Changes Diff](./A100_CODE_DIFF.md) for exact changes to make.

---

## 📋 Pre-Deployment Requirements

Before making any code changes, ensure:

1. ✅ **Budget Approval**: $3,760-$13,620/month for A100 GPUs
2. ✅ **Policy Exemption**: Request at https://aka.ms/AzPolicyWiki
3. ✅ **Quota Available**: Check NCadsA100v4 vCPU quota in your region
4. ✅ **Stakeholder Sign-off**: Team approval for cost increase

---

## 🎯 What Changes

### Critical Changes (Required)
- `infra/main.bicep` - 4 parameter updates
- `k8s/kaito-workspace.yaml` - 1 VM size update
- `k8s/kaito-foundry-workspace.yaml` - 1 VM size update

### Recommended Changes
- `infra/core/aks/aks-cluster.bicep` - 3 default parameter updates
- Model upgrades (optional)

### Total Effort
- **Files**: 4
- **Lines**: ~15
- **Time**: 10 minutes (manual) or 2 minutes (automated)

---

## 💰 Cost Impact

| Configuration | Monthly Cost | Annual Cost |
|--------------|-------------|-------------|
| **Current (T4 disabled)** | $475 | $5,700 |
| **A100 (1 node min)** | $3,760 | $45,120 |
| **A100 (4 nodes max)** | $13,620 | $163,440 |

**Cost Optimization**: Scale to zero in dev, use reserved instances in prod.

---

## 📊 Performance Improvement

| Metric | T4 | A100 | Improvement |
|--------|----|----|-------------|
| **GPU Memory** | 16 GB | 40 GB | +150% |
| **FP32 Performance** | 8.1 TFLOPS | 19.5 TFLOPS | +140% |
| **Tensor Performance** | 65 TFLOPS | 312 TFLOPS | +380% |
| **Memory Bandwidth** | 300 GB/s | 1,555 GB/s | +418% |

**Result**: ~10x faster inference for large language models.

---

## 🔄 Deployment Workflow

```
1. Pre-Approval (1-8 days)
   ├── Budget approval
   ├── Policy exemption
   └── Quota verification
   
2. Code Changes (10 minutes)
   ├── Run automated script
   └── Verify with git diff
   
3. Infrastructure Deployment (30 minutes)
   ├── azd up
   └── Verify GPU nodes
   
4. Kaito Installation (15 minutes)
   ├── Install operator
   └── Verify CRDs
   
5. Model Deployment (15 minutes)
   ├── Apply workspace
   └── Wait for model download
   
6. Testing & Validation (2 hours)
   ├── Infrastructure tests
   ├── GPU tests
   └── Model inference tests
```

**Total Time**: 2-11 days (mostly waiting for approvals)

---

## 🛟 Troubleshooting

### Policy Error
```
Error: RequestDisallowedByPolicy
```
**Solution**: Submit exemption request at https://aka.ms/AzPolicyWiki

### Quota Error
```
Error: Operation could not be completed as it results in exceeding approved quota
```
**Solution**: Request NCadsA100v4 vCPU quota increase via Azure Portal

### Node Not Scheduling
```
0/X nodes available: insufficient nvidia.com/gpu
```
**Solution**: Verify GPU node pool running: `kubectl get nodes -l kaito=true`

---

## 🔙 Rollback

### Quick Scale-Down (No code changes)
```powershell
az aks nodepool scale --resource-group rg-apim-mcp-aks-kaito --cluster-name aks-jozz4mn7tla5s --name gpupool --node-count 0
```
**Saves**: ~$3,285/month immediately

### Full Rollback (Revert to T4)
```powershell
git checkout v1.0-t4-gpu
azd up
```

---

## 📞 Support

### Documentation Files
- [Full Deployment Plan](./A100_GPU_DEPLOYMENT_PLAN.md) - Complete guide
- [Quick Reference](./A100_CHANGES_SUMMARY.md) - Fast lookup
- [Code Diff](./A100_CODE_DIFF.md) - Exact changes
- [Complete Inventory](./A100_INVENTORY.md) - Exhaustive checklist

### External Resources
- Azure Policy: https://aka.ms/AzPolicyWiki
- A100 VMs: https://learn.microsoft.com/azure/virtual-machines/nca100-v4-series
- Kaito: https://github.com/kaito-project/kaito
- AKS GPU: https://learn.microsoft.com/azure/aks/gpu-cluster

---

## ✅ Success Criteria

- [ ] GPU node pool created with A100 VMs
- [ ] Kaito operator installed and healthy
- [ ] Language model deployed and responding
- [ ] All tests passing (11/11 + new GPU tests)
- [ ] Model inference latency < 500ms (p95)
- [ ] Monthly spend within budget
- [ ] Documentation updated

---

## 🏁 Next Steps

1. **Read** [Quick Changes Summary](./A100_CHANGES_SUMMARY.md)
2. **Review** cost impact with stakeholders
3. **Request** Azure Policy exemption
4. **Verify** GPU quota availability
5. **Run** `.\scripts\apply-a100-changes.ps1 -DryRun`
6. **Deploy** with `azd up`

---

**Last Updated**: October 22, 2025  
**Version**: 1.0  
**Status**: Ready for deployment (pending policy exemption)
