# Apply A100 GPU Configuration Changes
# This script automatically updates all files to use A100 GPUs instead of T4 GPUs

param(
    [switch]$DryRun = $false,
    [switch]$UpgradeModels = $false
)

Write-Host ""
Write-Host "🚀 A100 GPU Configuration Update Script" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green
Write-Host ""

if ($DryRun) {
    Write-Host "🔍 DRY RUN MODE - No files will be modified" -ForegroundColor Yellow
    Write-Host ""
}

# Create backup directory
$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$backupDir = ".\backup-$timestamp"

if (-not $DryRun) {
    New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
    Write-Host "📦 Created backup directory: $backupDir" -ForegroundColor Cyan
}

# Files to modify
$files = @(
    "infra\main.bicep",
    "infra\core\aks\aks-cluster.bicep",
    "k8s\kaito-workspace.yaml",
    "k8s\kaito-foundry-workspace.yaml"
)

# Verify all files exist
$missingFiles = @()
foreach ($file in $files) {
    if (-not (Test-Path $file)) {
        $missingFiles += $file
    }
}

if ($missingFiles.Count -gt 0) {
    Write-Host "❌ ERROR: Missing files:" -ForegroundColor Red
    foreach ($file in $missingFiles) {
        Write-Host "   - $file" -ForegroundColor Red
    }
    Write-Host ""
    Write-Host "Please run this script from the repository root directory." -ForegroundColor Yellow
    exit 1
}

# Backup files
if (-not $DryRun) {
    Write-Host ""
    Write-Host "📋 Backing up files..." -ForegroundColor Cyan
    foreach ($file in $files) {
        $backupFile = Join-Path $backupDir ($file -replace '\\', '_')
        Copy-Item $file $backupFile
        Write-Host "   ✅ Backed up: $file" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "✏️  Applying changes..." -ForegroundColor Cyan
Write-Host ""

# Change 1: infra\main.bicep
Write-Host "📝 File 1/4: infra\main.bicep" -ForegroundColor Yellow
$file = "infra\main.bicep"
$content = Get-Content $file -Raw
$changes = 0

# VM Size
if ($content -match "gpuNodePoolVmSize: 'Standard_NC4as_T4_v3'") {
    Write-Host "   ✅ Changing GPU VM size: T4 → A100" -ForegroundColor Green
    $content = $content -replace "gpuNodePoolVmSize: 'Standard_NC4as_T4_v3'", "gpuNodePoolVmSize: 'Standard_NC24ads_A100_v4'"
    $changes++
} else {
    Write-Host "   ⏭️  GPU VM size already updated or not found" -ForegroundColor Gray
}

# Min Count
if ($content -match "gpuNodePoolMinCount: 0") {
    Write-Host "   ✅ Changing min count: 0 → 1" -ForegroundColor Green
    $content = $content -replace "gpuNodePoolMinCount: 0", "gpuNodePoolMinCount: 1"
    $changes++
} else {
    Write-Host "   ⏭️  Min count already updated or not found" -ForegroundColor Gray
}

# Max Count
if ($content -match "gpuNodePoolMaxCount: 3") {
    Write-Host "   ✅ Changing max count: 3 → 4" -ForegroundColor Green
    $content = $content -replace "gpuNodePoolMaxCount: 3", "gpuNodePoolMaxCount: 4"
    $changes++
} else {
    Write-Host "   ⏭️  Max count already updated or not found" -ForegroundColor Gray
}

# Enable GPU
if ($content -match "enableGpuNodePool: false") {
    Write-Host "   ✅ Enabling GPU node pool: false → true" -ForegroundColor Green
    $content = $content -replace "enableGpuNodePool: false", "enableGpuNodePool: true"
    $changes++
} else {
    Write-Host "   ⏭️  GPU node pool already enabled or not found" -ForegroundColor Gray
}

if (-not $DryRun -and $changes -gt 0) {
    Set-Content $file $content -NoNewline
}
Write-Host "   📊 Total changes: $changes" -ForegroundColor Cyan
Write-Host ""

# Change 2: infra\core\aks\aks-cluster.bicep
Write-Host "📝 File 2/4: infra\core\aks\aks-cluster.bicep" -ForegroundColor Yellow
$file = "infra\core\aks\aks-cluster.bicep"
$content = Get-Content $file -Raw
$changes = 0

# VM Size default
if ($content -match "param gpuNodePoolVmSize string = 'Standard_NC4as_T4_v3'") {
    Write-Host "   ✅ Changing default GPU VM size: T4 → A100" -ForegroundColor Green
    $content = $content -replace "param gpuNodePoolVmSize string = 'Standard_NC4as_T4_v3'", "param gpuNodePoolVmSize string = 'Standard_NC24ads_A100_v4'"
    $changes++
} else {
    Write-Host "   ⏭️  Default GPU VM size already updated or not found" -ForegroundColor Gray
}

# Min Count default
if ($content -match "param gpuNodePoolMinCount int = 0") {
    Write-Host "   ✅ Changing default min count: 0 → 1" -ForegroundColor Green
    $content = $content -replace "param gpuNodePoolMinCount int = 0", "param gpuNodePoolMinCount int = 1"
    $changes++
} else {
    Write-Host "   ⏭️  Default min count already updated or not found" -ForegroundColor Gray
}

# Max Count default
if ($content -match "param gpuNodePoolMaxCount int = 3") {
    Write-Host "   ✅ Changing default max count: 3 → 4" -ForegroundColor Green
    $content = $content -replace "param gpuNodePoolMaxCount int = 3", "param gpuNodePoolMaxCount int = 4"
    $changes++
} else {
    Write-Host "   ⏭️  Default max count already updated or not found" -ForegroundColor Gray
}

if (-not $DryRun -and $changes -gt 0) {
    Set-Content $file $content -NoNewline
}
Write-Host "   📊 Total changes: $changes" -ForegroundColor Cyan
Write-Host ""

# Change 3: k8s\kaito-workspace.yaml
Write-Host "📝 File 3/4: k8s\kaito-workspace.yaml" -ForegroundColor Yellow
$file = "k8s\kaito-workspace.yaml"
$content = Get-Content $file -Raw
$changes = 0

# VM Size
if ($content -match "instanceType: Standard_NC6s_v3") {
    Write-Host "   ✅ Changing instance type: Standard_NC6s_v3 → Standard_NC24ads_A100_v4" -ForegroundColor Green
    $content = $content -replace "instanceType: Standard_NC6s_v3", "instanceType: Standard_NC24ads_A100_v4"
    $changes++
} else {
    Write-Host "   ⏭️  Instance type already updated or not found" -ForegroundColor Gray
}

# Optional: Upgrade model
if ($UpgradeModels) {
    if ($content -match "name: phi-3-mini-4k-instruct") {
        Write-Host "   ✅ Upgrading model: phi-3-mini-4k → phi-3-medium-128k" -ForegroundColor Green
        $content = $content -replace "name: phi-3-mini-4k-instruct", "name: phi-3-medium-128k-instruct"
        $changes++
    }
    
    # Add workload: gpu label if not present
    if ($content -match 'matchLabels:\s+kaito: "true"' -and $content -notmatch 'workload: "gpu"') {
        Write-Host "   ✅ Adding workload label: gpu" -ForegroundColor Green
        $content = $content -replace '(matchLabels:\s+kaito: "true")', '$1`n        workload: "gpu"'
        $changes++
    }
} else {
    Write-Host "   ⏭️  Model upgrade skipped (use -UpgradeModels flag to enable)" -ForegroundColor Gray
}

if (-not $DryRun -and $changes -gt 0) {
    Set-Content $file $content -NoNewline
}
Write-Host "   📊 Total changes: $changes" -ForegroundColor Cyan
Write-Host ""

# Change 4: k8s\kaito-foundry-workspace.yaml
Write-Host "📝 File 4/4: k8s\kaito-foundry-workspace.yaml" -ForegroundColor Yellow
$file = "k8s\kaito-foundry-workspace.yaml"
$content = Get-Content $file -Raw
$changes = 0

# VM Size
if ($content -match "instanceType: Standard_NC6s_v3") {
    Write-Host "   ✅ Changing instance type: Standard_NC6s_v3 → Standard_NC24ads_A100_v4" -ForegroundColor Green
    $content = $content -replace "instanceType: Standard_NC6s_v3", "instanceType: Standard_NC24ads_A100_v4"
    $changes++
} else {
    Write-Host "   ⏭️  Instance type already updated or not found" -ForegroundColor Gray
}

# Optional: Upgrade model
if ($UpgradeModels) {
    if ($content -match "name: phi-3-mini-4k-instruct") {
        Write-Host "   ✅ Upgrading model: phi-3-mini-4k → llama-2-7b-chat" -ForegroundColor Green
        $content = $content -replace "name: phi-3-mini-4k-instruct", "name: llama-2-7b-chat"
        $changes++
    }
} else {
    Write-Host "   ⏭️  Model upgrade skipped (use -UpgradeModels flag to enable)" -ForegroundColor Gray
}

if (-not $DryRun -and $changes -gt 0) {
    Set-Content $file $content -NoNewline
}
Write-Host "   📊 Total changes: $changes" -ForegroundColor Cyan
Write-Host ""

# Summary
Write-Host "=========================================" -ForegroundColor Green
if ($DryRun) {
    Write-Host "🔍 DRY RUN COMPLETE - No files were modified" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To apply changes, run without -DryRun flag:" -ForegroundColor Cyan
    Write-Host "   .\scripts\apply-a100-changes.ps1" -ForegroundColor White
} else {
    Write-Host "✅ All changes applied successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📦 Backups saved to: $backupDir" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "📋 Next Steps:" -ForegroundColor Yellow
Write-Host "   1. Review changes:  git diff" -ForegroundColor White
Write-Host "   2. Verify policy exemption is approved" -ForegroundColor White
Write-Host "   3. Check quota availability" -ForegroundColor White
Write-Host "   4. Deploy infrastructure:  azd up" -ForegroundColor White
Write-Host "   5. Install Kaito:  .\scripts\install-kaito.ps1" -ForegroundColor White
Write-Host "   6. Deploy model:  kubectl apply -f k8s\kaito-foundry-workspace.yaml" -ForegroundColor White
Write-Host ""

Write-Host "📚 Documentation:" -ForegroundColor Yellow
Write-Host "   - Full plan: docs\A100_GPU_DEPLOYMENT_PLAN.md" -ForegroundColor White
Write-Host "   - Quick ref:  docs\A100_CHANGES_SUMMARY.md" -ForegroundColor White
Write-Host "   - Code diff:  docs\A100_CODE_DIFF.md" -ForegroundColor White
Write-Host ""
