#!/bin/bash
# Install Kaito operator on AKS cluster

set -e

echo "🚀 Installing Kaito operator on AKS..."

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl not found. Please install kubectl first."
    exit 1
fi

# Check if helm is available
if ! command -v helm &> /dev/null; then
    echo "❌ Helm not found. Please install Helm first."
    exit 1
fi

# Add Kaito Helm repository
echo "📦 Adding Kaito Helm repository..."
helm repo add kaito https://azure.github.io/kaito
helm repo update

# Install Kaito workspace CRDs
echo "📋 Installing Kaito CRDs..."
kubectl apply -f https://raw.githubusercontent.com/kaito-project/kaito/main/charts/kaito/workspace/crds/kaito.sh_workspaces.yaml

# Install Kaito operator
echo "⚙️  Installing Kaito operator..."
helm upgrade --install kaito kaito/kaito \
    --namespace kaito-system \
    --create-namespace \
    --set image.repository=mcr.microsoft.com/aks/kaito/workspace \
    --wait

echo "✅ Kaito operator installed successfully!"

# Verify installation
echo "🔍 Verifying Kaito installation..."
kubectl get pods -n kaito-system

echo ""
echo "✅ Kaito is ready!"
echo "📝 You can now apply Kaito Workspace CRDs to deploy models."
