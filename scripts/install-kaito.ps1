# Install Kaito operator on AKS cluster
# PowerShell version

$ErrorActionPreference = "Stop"

Write-Host "🚀 Installing Kaito operator on AKS..." -ForegroundColor Cyan

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
Write-Host "📦 Adding Kaito Helm repository..." -ForegroundColor Yellow
helm repo add kaito https://azure.github.io/kaito
helm repo update

# Install Kaito workspace CRDs
Write-Host "📋 Installing Kaito CRDs..." -ForegroundColor Yellow
kubectl apply -f https://raw.githubusercontent.com/kaito-project/kaito/main/charts/kaito/workspace/crds/kaito.sh_workspaces.yaml

# Install Kaito operator
Write-Host "⚙️  Installing Kaito operator..." -ForegroundColor Yellow
helm upgrade --install kaito kaito/kaito `
    --namespace kaito-system `
    --create-namespace `
    --set image.repository=mcr.microsoft.com/aks/kaito/workspace `
    --wait

Write-Host "✅ Kaito operator installed successfully!" -ForegroundColor Green

# Verify installation
Write-Host "🔍 Verifying Kaito installation..." -ForegroundColor Yellow
kubectl get pods -n kaito-system

Write-Host ""
Write-Host "✅ Kaito is ready!" -ForegroundColor Green
Write-Host "📝 You can now apply Kaito Workspace CRDs to deploy models." -ForegroundColor Cyan
