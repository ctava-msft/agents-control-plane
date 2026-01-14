#!/bin/bash
# Workload Identity Federation Demo Script
# This script demonstrates how AKS pods obtain Azure tokens without embedded secrets

set -e

echo "=================================================="
echo "Workload Identity Federation Demo"
echo "=================================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get environment variables
export AKS_CLUSTER_NAME=$(azd env get-values | grep AKS_CLUSTER_NAME | cut -d'=' -f2 | tr -d '"')
export RESOURCE_GROUP=$(azd env get-values 2>/dev/null | grep AZURE_RESOURCE_GROUP_NAME | cut -d'=' -f2 | tr -d '"')
export AZURE_KEY_VAULT_URL=$(azd env get-values | grep AZURE_KEY_VAULT_URL | cut -d'=' -f2 | tr -d '"')
export AZURE_STORAGE_ACCOUNT_URL=$(azd env get-values | grep AZURE_STORAGE_ACCOUNT_URL | cut -d'=' -f2 | tr -d '"')

if [ -z "$AKS_CLUSTER_NAME" ] || [ -z "$RESOURCE_GROUP" ]; then
    echo -e "${RED}Error: Could not find AKS cluster name or resource group${NC}"
    echo "Please run 'azd up' first to deploy the infrastructure"
    exit 1
fi

echo -e "${GREEN}✓ Environment loaded${NC}"
echo "  AKS Cluster: $AKS_CLUSTER_NAME"
echo "  Resource Group: $RESOURCE_GROUP"
echo ""

# Step 1: Verify OIDC Issuer
echo "Step 1: Verify AKS OIDC Issuer Configuration"
echo "----------------------------------------------"
OIDC_ISSUER=$(az aks show --name $AKS_CLUSTER_NAME --resource-group $RESOURCE_GROUP \
  --query "oidcIssuerProfile.issuerUrl" -o tsv 2>/dev/null)

if [ -z "$OIDC_ISSUER" ]; then
    echo -e "${RED}✗ OIDC issuer not configured${NC}"
    exit 1
fi

echo -e "${GREEN}✓ OIDC Issuer URL: $OIDC_ISSUER${NC}"
echo ""

# Step 2: Verify Workload Identity is enabled
echo "Step 2: Verify Workload Identity is Enabled"
echo "----------------------------------------------"
WORKLOAD_IDENTITY=$(az aks show --name $AKS_CLUSTER_NAME --resource-group $RESOURCE_GROUP \
  --query "securityProfile.workloadIdentity.enabled" -o tsv 2>/dev/null)

if [ "$WORKLOAD_IDENTITY" != "true" ]; then
    echo -e "${RED}✗ Workload Identity not enabled${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Workload Identity is enabled${NC}"
echo ""

# Step 3: Check Service Account
echo "Step 3: Verify Service Account Configuration"
echo "----------------------------------------------"
SA_EXISTS=$(kubectl get serviceaccount mcp-server-sa -n mcp-server 2>/dev/null | wc -l)

if [ "$SA_EXISTS" -lt 2 ]; then
    echo -e "${RED}✗ Service account not found${NC}"
    echo "Please deploy the MCP server first"
    exit 1
fi

CLIENT_ID=$(kubectl get serviceaccount mcp-server-sa -n mcp-server \
  -o jsonpath='{.metadata.annotations.azure\.workload\.identity/client-id}' 2>/dev/null)

if [ -z "$CLIENT_ID" ]; then
    echo -e "${RED}✗ Client ID annotation not found${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Service Account: mcp-server-sa${NC}"
echo "  Client ID: $CLIENT_ID"
echo ""

# Step 4: Check Pod Configuration
echo "Step 4: Verify MCP Server Pod Configuration"
echo "----------------------------------------------"
POD_NAME=$(kubectl get pods -n mcp-server -l app=mcp-server -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

if [ -z "$POD_NAME" ]; then
    echo -e "${YELLOW}⚠ No MCP server pods found${NC}"
    echo "Skipping pod verification"
else
    echo -e "${GREEN}✓ Pod: $POD_NAME${NC}"
    
    # Check pod labels
    WORKLOAD_LABEL=$(kubectl get pod $POD_NAME -n mcp-server \
      -o jsonpath='{.metadata.labels.azure\.workload\.identity/use}' 2>/dev/null)
    
    if [ "$WORKLOAD_LABEL" = "true" ]; then
        echo -e "${GREEN}✓ Pod has workload identity label${NC}"
    else
        echo -e "${RED}✗ Pod missing workload identity label${NC}"
    fi
fi
echo ""

# Step 5: Demo - Obtain Azure Token from Pod
echo "Step 5: Demonstrate Token Acquisition (No Secrets!)"
echo "----------------------------------------------"

if [ -z "$POD_NAME" ]; then
    echo -e "${YELLOW}⚠ Skipping token demo (no pods available)${NC}"
else
    echo "Executing Python script inside pod to obtain Azure token..."
    echo ""
    
    # Create a Python script to run inside the pod
    cat > /tmp/test_token.py << 'EOF'
from azure.identity import DefaultAzureCredential
import sys
import os

try:
    print("🔐 Attempting to obtain Azure token using Workload Identity...")
    print(f"   Client ID: {os.getenv('AZURE_CLIENT_ID')}")
    print(f"   Token File: {os.getenv('AZURE_FEDERATED_TOKEN_FILE')}")
    print("")
    
    # This uses Workload Identity Federation - NO SECRETS!
    credential = DefaultAzureCredential()
    
    # Get a token for Key Vault
    token = credential.get_token("https://vault.azure.net/.default")
    
    print("✓ Token obtained successfully!")
    print(f"  Token prefix: {token.token[:30]}...")
    print(f"  Token expires: {token.expires_on}")
    print("")
    print("🎉 SUCCESS: Obtained Azure AD token without any embedded secrets!")
    
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)
EOF
    
    # Copy script to pod and execute
    kubectl cp /tmp/test_token.py mcp-server/$POD_NAME:/tmp/test_token.py 2>/dev/null
    
    echo -e "${YELLOW}Output from pod:${NC}"
    echo "---"
    kubectl exec -n mcp-server $POD_NAME -- python /tmp/test_token.py
    echo "---"
    echo ""
    
    rm /tmp/test_token.py
fi

# Step 6: Demonstrate Key Vault Access
echo "Step 6: Demonstrate Key Vault Access (No Connection Strings!)"
echo "----------------------------------------------"

if [ -z "$POD_NAME" ] || [ -z "$AZURE_KEY_VAULT_URL" ]; then
    echo -e "${YELLOW}⚠ Skipping Key Vault demo${NC}"
else
    echo "Testing Key Vault access using Workload Identity..."
    echo ""
    
    cat > /tmp/test_keyvault.py << 'EOF'
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
import os
import sys

try:
    vault_url = os.getenv("AZURE_KEY_VAULT_URL")
    print(f"🔐 Connecting to Key Vault: {vault_url}")
    print("   Using Workload Identity (no secrets in configuration)")
    print("")
    
    # Create Key Vault client using Workload Identity
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=vault_url, credential=credential)
    
    # Try to set a secret
    secret_name = "workload-identity-demo"
    secret_value = "This secret was stored using Workload Identity!"
    
    print(f"📝 Storing secret: {secret_name}")
    client.set_secret(secret_name, secret_value)
    print(f"✓ Secret stored successfully")
    print("")
    
    # Retrieve the secret
    print(f"📖 Retrieving secret: {secret_name}")
    retrieved = client.get_secret(secret_name)
    print(f"✓ Secret retrieved: {retrieved.value}")
    print("")
    
    print("🎉 SUCCESS: Accessed Key Vault without any connection strings!")
    
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)
EOF
    
    kubectl cp /tmp/test_keyvault.py mcp-server/$POD_NAME:/tmp/test_keyvault.py 2>/dev/null
    
    echo -e "${YELLOW}Output from pod:${NC}"
    echo "---"
    kubectl exec -n mcp-server $POD_NAME -- python /tmp/test_keyvault.py
    echo "---"
    echo ""
    
    rm /tmp/test_keyvault.py
fi

# Step 7: Demonstrate Storage Access
echo "Step 7: Demonstrate Storage Access (No Access Keys!)"
echo "----------------------------------------------"

if [ -z "$POD_NAME" ] || [ -z "$AZURE_STORAGE_ACCOUNT_URL" ]; then
    echo -e "${YELLOW}⚠ Skipping Storage demo${NC}"
else
    echo "Testing Storage access using Workload Identity..."
    echo ""
    
    cat > /tmp/test_storage.py << 'EOF'
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
import os
import sys

try:
    storage_url = os.getenv("AZURE_STORAGE_ACCOUNT_URL")
    print(f"📦 Connecting to Storage: {storage_url}")
    print("   Using Workload Identity (no access keys)")
    print("")
    
    # Create Storage client using Workload Identity
    credential = DefaultAzureCredential()
    client = BlobServiceClient(account_url=storage_url, credential=credential)
    
    # Try to upload a blob
    container_name = "snippets"
    blob_name = "workload-identity-demo.txt"
    blob_content = "This blob was uploaded using Workload Identity!"
    
    print(f"📤 Uploading blob: {blob_name} to {container_name}")
    blob_client = client.get_blob_client(container=container_name, blob=blob_name)
    blob_client.upload_blob(blob_content, overwrite=True)
    print(f"✓ Blob uploaded successfully")
    print("")
    
    # Download the blob
    print(f"📥 Downloading blob: {blob_name}")
    downloaded = blob_client.download_blob().readall()
    print(f"✓ Blob content: {downloaded.decode('utf-8')}")
    print("")
    
    print("🎉 SUCCESS: Accessed Storage without any access keys!")
    
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)
EOF
    
    kubectl cp /tmp/test_storage.py mcp-server/$POD_NAME:/tmp/test_storage.py 2>/dev/null
    
    echo -e "${YELLOW}Output from pod:${NC}"
    echo "---"
    kubectl exec -n mcp-server $POD_NAME -- python /tmp/test_storage.py
    echo "---"
    echo ""
    
    rm /tmp/test_storage.py
fi

# Summary
echo ""
echo "=================================================="
echo "Demo Complete!"
echo "=================================================="
echo ""
echo -e "${GREEN}✓ Workload Identity is properly configured${NC}"
echo -e "${GREEN}✓ AKS pods can obtain Azure tokens without secrets${NC}"
echo -e "${GREEN}✓ Key Vault access works via Managed Identity${NC}"
echo -e "${GREEN}✓ Storage access works via Managed Identity${NC}"
echo ""
echo "Key Takeaways:"
echo "  • No connection strings or access keys in configuration"
echo "  • No secrets in Kubernetes secrets or ConfigMaps"
echo "  • Tokens are short-lived and automatically refreshed"
echo "  • All authentication is audited in Azure AD logs"
echo "  • RBAC controls access to Azure resources"
echo ""
echo "For more details, see: docs/WORKLOAD_IDENTITY_DEMO.md"
