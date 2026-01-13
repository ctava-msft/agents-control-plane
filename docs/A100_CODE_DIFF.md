# A100 GPU Deployment - Code Changes Diff

This document shows the exact line-by-line changes needed to migrate from T4 GPUs to A100 GPUs.

---

## File 1: `infra/main.bicep`

### Location: Lines 150-156

**BEFORE:**
```bicep
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
    gpuNodePoolVmSize: 'Standard_NC4as_T4_v3'
    gpuNodePoolMinCount: 0
    gpuNodePoolMaxCount: 3
    enableGpuNodePool: false
    userAssignedIdentityId: aksUserAssignedIdentity.outputs.identityId
    logAnalyticsWorkspaceId: monitoring.outputs.logAnalyticsWorkspaceId
    subnetId: vnetEnabled ? '${rg.id}/providers/Microsoft.Network/virtualNetworks/${serviceVirtualNetworkName}/subnets/${serviceVirtualNetworkAppSubnetName}' : ''
  }
  dependsOn: vnetEnabled ? [
    serviceVirtualNetworkEarly
  ] : []
}
```

**AFTER:**
```bicep
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
    gpuNodePoolVmSize: 'Standard_NC24ads_A100_v4'     // ✏️ CHANGED
    gpuNodePoolMinCount: 1                             // ✏️ CHANGED
    gpuNodePoolMaxCount: 4                             // ✏️ CHANGED
    enableGpuNodePool: true                            // ✏️ CHANGED
    userAssignedIdentityId: aksUserAssignedIdentity.outputs.identityId
    logAnalyticsWorkspaceId: monitoring.outputs.logAnalyticsWorkspaceId
    subnetId: vnetEnabled ? '${rg.id}/providers/Microsoft.Network/virtualNetworks/${serviceVirtualNetworkName}/subnets/${serviceVirtualNetworkAppSubnetName}' : ''
  }
  dependsOn: vnetEnabled ? [
    serviceVirtualNetworkEarly
  ] : []
}
```

**Changes:**
- Line 151: `'Standard_NC4as_T4_v3'` → `'Standard_NC24ads_A100_v4'`
- Line 152: `0` → `1`
- Line 153: `3` → `4`
- Line 154: `false` → `true`

---

## File 2: `infra/core/aks/aks-cluster.bicep`

### Location: Lines 19-26

**BEFORE:**
```bicep
@description('GPU node pool VM size for Kaito workloads')
param gpuNodePoolVmSize string = 'Standard_NC4as_T4_v3'

@description('GPU node pool min count')
param gpuNodePoolMinCount int = 0

@description('GPU node pool max count')
param gpuNodePoolMaxCount int = 3
```

**AFTER:**
```bicep
@description('GPU node pool VM size for Kaito workloads')
param gpuNodePoolVmSize string = 'Standard_NC24ads_A100_v4'  // ✏️ CHANGED

@description('GPU node pool min count')
param gpuNodePoolMinCount int = 1                             // ✏️ CHANGED

@description('GPU node pool max count')
param gpuNodePoolMaxCount int = 4                             // ✏️ CHANGED
```

**Changes:**
- Line 20: Default VM size changed to A100
- Line 23: Default min count increased to 1
- Line 26: Default max count increased to 4

### Location: Lines 43-44 (OPTIONAL)

**BEFORE:**
```bicep
@description('Enable GPU node pool (requires policy exemption in some subscriptions)')
param enableGpuNodePool bool = false
```

**AFTER (OPTIONAL):**
```bicep
@description('Enable GPU node pool (requires policy exemption in some subscriptions)')
param enableGpuNodePool bool = true  // ✏️ CHANGED (optional)
```

**Note**: This change is optional since `main.bicep` will override this anyway.

---

## File 3: `k8s/kaito-workspace.yaml`

### Location: Lines 8 and 17

**BEFORE:**
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
      # Use Phi-3-mini as the base model (can be changed to other Foundry models)
      name: phi-3-mini-4k-instruct
      # Pull from Azure Foundry registry
      # The image will be pulled from Azure Container Registry linked to Foundry
  
  # Resource requirements
  resource:
    # Number of GPU nodes
    count: 1
    # Instance type - GPU enabled
    instanceType: Standard_NC6s_v3
    # Node selector to target GPU node pool
    labelSelector:
      matchLabels:
        kaito: "true"
```

**AFTER:**
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
      # Use Phi-3-medium to take advantage of A100 memory and performance
      name: phi-3-medium-128k-instruct                     # ✏️ CHANGED (optional upgrade)
      # Pull from Azure Foundry registry
      # The image will be pulled from Azure Container Registry linked to Foundry
  
  # Resource requirements
  resource:
    # Number of GPU nodes
    count: 1
    # Instance type - GPU enabled
    instanceType: Standard_NC24ads_A100_v4                 # ✏️ CHANGED
    # Node selector to target GPU node pool
    labelSelector:
      matchLabels:
        kaito: "true"
        workload: "gpu"                                    # ✏️ ADDED for safety
```

**Changes:**
- Line 11: Model upgraded from `phi-3-mini-4k-instruct` to `phi-3-medium-128k-instruct` (optional)
- Line 20: VM size changed to `Standard_NC24ads_A100_v4`
- Line 24: Added `workload: "gpu"` label selector (recommended)

---

## File 4: `k8s/kaito-foundry-workspace.yaml`

### Location: Lines 14 and 27

**BEFORE:**
```yaml
apiVersion: kaito.sh/v1alpha1
kind: Workspace
metadata:
  name: azure-foundry-model
  namespace: default
  annotations:
    description: "Workspace for deploying Azure Foundry models via Kaito"
spec:
  # Model inference configuration using Azure Foundry registry
  inference:
    # Custom preset configuration for Azure Foundry models
    preset:
      # Phi-3 models from Azure Foundry
      # Can be changed to: phi-3-mini-128k-instruct, phi-3-medium, etc.
      name: phi-3-mini-4k-instruct
      
    # Alternative: Use custom image from Azure Foundry registry
    # template:
    #   image: <your-acr>.azurecr.io/foundry/phi-3-mini-4k-instruct:latest
    #   imagePullPolicy: IfNotPresent
  
  # Resource requirements for model deployment
  resource:
    # Number of instances (GPU nodes)
    count: 1
    
    # GPU-enabled VM size
    # Options: Standard_NC6s_v3, Standard_NC12s_v3, Standard_NC24s_v3
    # Or: Standard_ND40rs_v2 (for larger models)
    instanceType: Standard_NC6s_v3
    
    # Label selector to target GPU node pool created by Bicep
    labelSelector:
      matchLabels:
        kaito: "true"
        workload: "gpu"
```

**AFTER:**
```yaml
apiVersion: kaito.sh/v1alpha1
kind: Workspace
metadata:
  name: azure-foundry-model
  namespace: default
  annotations:
    description: "Workspace for deploying Azure Foundry models via Kaito on A100 GPU"  # ✏️ UPDATED
spec:
  # Model inference configuration using Azure Foundry registry
  inference:
    # Custom preset configuration for Azure Foundry models
    preset:
      # Upgraded to larger model that benefits from A100 performance
      name: llama-2-7b-chat                                # ✏️ CHANGED (recommended upgrade)
      
    # Alternative: Use custom image from Azure Foundry registry
    # template:
    #   image: <your-acr>.azurecr.io/foundry/llama-2-7b-chat:latest
    #   imagePullPolicy: IfNotPresent
  
  # Resource requirements for model deployment
  resource:
    # Number of instances (GPU nodes)
    count: 1
    
    # GPU-enabled VM size - A100 40GB
    # Options: Standard_NC24ads_A100_v4, Standard_NC48ads_A100_v4, Standard_NC96ads_A100_v4
    # Or: Standard_ND96asr_v4 (8x A100 for largest models)
    instanceType: Standard_NC24ads_A100_v4                 # ✏️ CHANGED
    
    # Label selector to target GPU node pool created by Bicep
    labelSelector:
      matchLabels:
        kaito: "true"
        workload: "gpu"
```

**Changes:**
- Line 7: Updated description to mention A100
- Line 15: Model upgraded to `llama-2-7b-chat` (recommended but optional)
- Line 30: VM size changed to `Standard_NC24ads_A100_v4`
- Lines 28-29: Updated comments to reflect A100 options

---

## Summary of Changes

### Required Changes (MUST DO)
1. ✅ `infra/main.bicep` - 4 parameter changes
2. ✅ `k8s/kaito-workspace.yaml` - 1 VM size change
3. ✅ `k8s/kaito-foundry-workspace.yaml` - 1 VM size change

### Recommended Changes (SHOULD DO)
1. ✅ `infra/core/aks/aks-cluster.bicep` - Update defaults
2. ✅ `k8s/kaito-workspace.yaml` - Upgrade to larger model
3. ✅ `k8s/kaito-foundry-workspace.yaml` - Upgrade to larger model

### Total Changes
- **Files Modified**: 4
- **Lines Changed**: ~15
- **Estimated Time**: 10 minutes

---

## Verification Commands

After making changes, verify before deployment:

```powershell
# Check for A100 VM size references
Select-String -Path "infra\main.bicep" -Pattern "NC24ads_A100_v4"
Select-String -Path "infra\core\aks\aks-cluster.bicep" -Pattern "NC24ads_A100_v4"
Select-String -Path "k8s\kaito-*.yaml" -Pattern "NC24ads_A100_v4"

# Check enableGpuNodePool is true
Select-String -Path "infra\main.bicep" -Pattern "enableGpuNodePool: true"

# Check min count is at least 1
Select-String -Path "infra\main.bicep" -Pattern "gpuNodePoolMinCount"
```

---

## Apply Changes Script

You can use this PowerShell script to apply all changes automatically:

```powershell
# apply-a100-changes.ps1

Write-Host "🚀 Applying A100 GPU configuration changes..." -ForegroundColor Green

# Backup files
$backupDir = ".\backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
New-Item -ItemType Directory -Path $backupDir | Out-Null

Copy-Item "infra\main.bicep" "$backupDir\main.bicep.bak"
Copy-Item "infra\core\aks\aks-cluster.bicep" "$backupDir\aks-cluster.bicep.bak"
Copy-Item "k8s\kaito-workspace.yaml" "$backupDir\kaito-workspace.yaml.bak"
Copy-Item "k8s\kaito-foundry-workspace.yaml" "$backupDir\kaito-foundry-workspace.yaml.bak"

Write-Host "✅ Backups created in: $backupDir" -ForegroundColor Cyan

# Apply changes to main.bicep
$content = Get-Content "infra\main.bicep" -Raw
$content = $content -replace "gpuNodePoolVmSize: 'Standard_NC4as_T4_v3'", "gpuNodePoolVmSize: 'Standard_NC24ads_A100_v4'"
$content = $content -replace "gpuNodePoolMinCount: 0", "gpuNodePoolMinCount: 1"
$content = $content -replace "gpuNodePoolMaxCount: 3", "gpuNodePoolMaxCount: 4"
$content = $content -replace "enableGpuNodePool: false", "enableGpuNodePool: true"
Set-Content "infra\main.bicep" $content
Write-Host "✅ Updated: infra\main.bicep" -ForegroundColor Green

# Apply changes to aks-cluster.bicep
$content = Get-Content "infra\core\aks\aks-cluster.bicep" -Raw
$content = $content -replace "param gpuNodePoolVmSize string = 'Standard_NC4as_T4_v3'", "param gpuNodePoolVmSize string = 'Standard_NC24ads_A100_v4'"
$content = $content -replace "param gpuNodePoolMinCount int = 0", "param gpuNodePoolMinCount int = 1"
$content = $content -replace "param gpuNodePoolMaxCount int = 3", "param gpuNodePoolMaxCount int = 4"
Set-Content "infra\core\aks\aks-cluster.bicep" $content
Write-Host "✅ Updated: infra\core\aks\aks-cluster.bicep" -ForegroundColor Green

# Apply changes to kaito-workspace.yaml
$content = Get-Content "k8s\kaito-workspace.yaml" -Raw
$content = $content -replace "instanceType: Standard_NC6s_v3", "instanceType: Standard_NC24ads_A100_v4"
Set-Content "k8s\kaito-workspace.yaml" $content
Write-Host "✅ Updated: k8s\kaito-workspace.yaml" -ForegroundColor Green

# Apply changes to kaito-foundry-workspace.yaml
$content = Get-Content "k8s\kaito-foundry-workspace.yaml" -Raw
$content = $content -replace "instanceType: Standard_NC6s_v3", "instanceType: Standard_NC24ads_A100_v4"
Set-Content "k8s\kaito-foundry-workspace.yaml" $content
Write-Host "✅ Updated: k8s\kaito-foundry-workspace.yaml" -ForegroundColor Green

Write-Host ""
Write-Host "✅ All changes applied successfully!" -ForegroundColor Green
Write-Host "📝 Backups saved to: $backupDir" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Review changes: git diff" -ForegroundColor White
Write-Host "2. Ensure Azure Policy exemption is approved" -ForegroundColor White
Write-Host "3. Deploy: azd up" -ForegroundColor White
```

Save this script as `apply-a100-changes.ps1` and run it to automatically apply all changes.

---

**Ready to apply?** Run the deployment after:
1. ✅ Azure Policy exemption approved
2. ✅ Quota verified/increased
3. ✅ Code changes reviewed
4. ✅ Budget approved
