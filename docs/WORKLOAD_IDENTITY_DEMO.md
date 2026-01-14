# Workload Identity Federation Demo

This document demonstrates how to use Azure Entra Workload Identity Federation with AKS to obtain tokens without embedded secrets.

## Overview

Workload Identity Federation allows Kubernetes pods to authenticate to Azure services using their service account, without needing to manage secrets or certificates. This is achieved through OpenID Connect (OIDC) federation between AKS and Azure Entra ID.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  AKS Pod with Service Account                       │
│  ├── Service Account Token (Kubernetes)             │
│  └── Azure Workload Identity Sidecar                │
└──────────────────┬──────────────────────────────────┘
                   │ 1. Request Azure Token
                   ↓
┌─────────────────────────────────────────────────────┐
│  Azure Entra ID (Token Exchange)                    │
│  ├── Validates Kubernetes token via OIDC issuer     │
│  ├── Checks federated credential trust              │
│  └── Issues Azure AD token                          │
└──────────────────┬──────────────────────────────────┘
                   │ 2. Use Azure AD Token
                   ↓
┌─────────────────────────────────────────────────────┐
│  Azure Resources                                     │
│  ├── Key Vault (secrets access)                     │
│  ├── Storage Account (blob/queue access)            │
│  ├── Application Insights (telemetry)               │
│  └── Any Azure service with RBAC                    │
└─────────────────────────────────────────────────────┘
```

## Prerequisites

1. AKS cluster with OIDC Issuer enabled (already configured in this repo)
2. Workload Identity enabled on the cluster
3. Azure CLI and kubectl installed

## Demo: Obtain Entra Token Without Secrets

### Step 1: Verify Workload Identity Configuration

Check that your AKS cluster has OIDC issuer enabled:

```bash
export AKS_CLUSTER_NAME=$(azd env get-values | grep AKS_CLUSTER_NAME | cut -d'=' -f2 | tr -d '"')
export RESOURCE_GROUP=$(azd env get-values | grep AZURE_RESOURCE_GROUP_NAME | cut -d'=' -f2 | tr -d '"')

az aks show --name $AKS_CLUSTER_NAME --resource-group $RESOURCE_GROUP \
  --query "oidcIssuerProfile.issuerUrl" -o tsv
```

Expected output: `https://oidc.prod-aks.azure.com/xxxxx/`

### Step 2: Check Service Account Configuration

Inspect the MCP server service account:

```bash
kubectl get serviceaccount mcp-server-sa -n mcp-server -o yaml
```

Expected output:
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  annotations:
    azure.workload.identity/client-id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
  labels:
    azure.workload.identity/use: "true"
  name: mcp-server-sa
  namespace: mcp-server
```

### Step 3: Verify Pod Labels

Check that the MCP server pods have the workload identity label:

```bash
kubectl get pods -n mcp-server -o jsonpath='{.items[*].metadata.labels}' | jq
```

Expected: `"azure.workload.identity/use": "true"`

### Step 4: Exec Into Pod and Test Token Acquisition

Connect to a running MCP server pod:

```bash
POD_NAME=$(kubectl get pods -n mcp-server -l app=mcp-server -o jsonpath='{.items[0].metadata.name}')
kubectl exec -it $POD_NAME -n mcp-server -- /bin/sh
```

Inside the pod, verify the environment variables:

```bash
env | grep AZURE
```

Expected output:
```
AZURE_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_FEDERATED_TOKEN_FILE=/var/run/secrets/azure/tokens/azure-identity-token
AZURE_AUTHORITY_HOST=https://login.microsoftonline.com/
```

### Step 5: Obtain Azure AD Token Using DefaultAzureCredential

Run a Python script to obtain a token:

```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

# This uses Workload Identity Federation - no secrets needed!
credential = DefaultAzureCredential()

# Get a token for Azure Key Vault
token = credential.get_token("https://vault.azure.net/.default")

print(f"Token obtained successfully!")
print(f"Token type: {token.token[:20]}...")
print(f"Expires on: {token.expires_on}")
```

Save this as `test_token.py` and run:

```bash
python test_token.py
```

Expected output:
```
Token obtained successfully!
Token type: eyJ0eXAiOiJKV1QiLCJh...
Expires on: 1705234567
```

### Step 6: Use Token to Access Azure Resources

Test accessing Key Vault without any embedded secrets:

```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
import os

# No secrets or keys needed - uses Workload Identity!
credential = DefaultAzureCredential()
vault_url = os.getenv("AZURE_KEY_VAULT_URL")

client = SecretClient(vault_url=vault_url, credential=credential)

# Store a secret
client.set_secret("demo-secret", "Hello from Workload Identity!")

# Retrieve the secret
secret = client.get_secret("demo-secret")
print(f"Retrieved secret: {secret.value}")
```

### Step 7: Verify No Secrets in Configuration

Check that there are no secrets in environment variables or config files:

```bash
# No connection strings
echo $AZURE_STORAGE_CONNECTION_STRING
# Empty

# No access keys
kubectl get secret -n mcp-server
# Should only show service account tokens, no storage or vault keys

# Check deployment YAML
kubectl get deployment mcp-server -n mcp-server -o yaml | grep -i secret
# Should only reference service account, not any secret values
```

## How It Works

### 1. Federated Identity Credential

When you deploy with `azd up`, a federated identity credential is automatically created:

```bicep
resource federatedCredential 'Microsoft.ManagedIdentity/userAssignedIdentities/federatedIdentityCredentials@2023-01-31' = {
  parent: managedIdentity
  name: 'mcp-server-federation'
  properties: {
    issuer: aksCluster.properties.oidcIssuerProfile.issuerURL
    subject: 'system:serviceaccount:mcp-server:mcp-server-sa'
    audiences: [
      'api://AzureADTokenExchange'
    ]
  }
}
```

### 2. Token Exchange Flow

1. Pod requests access to Azure resource (e.g., Key Vault)
2. Azure Identity SDK reads Kubernetes service account token from:
   ```
   /var/run/secrets/azure/tokens/azure-identity-token
   ```
3. SDK exchanges Kubernetes token for Azure AD token via OIDC federation
4. Azure AD validates:
   - OIDC issuer matches AKS cluster issuer
   - Subject matches service account (`system:serviceaccount:mcp-server:mcp-server-sa`)
   - Audience is correct (`api://AzureADTokenExchange`)
5. Azure AD issues short-lived Azure AD token
6. SDK uses Azure AD token to access resource

### 3. RBAC Authorization

Once authenticated, access is controlled by Azure RBAC:
- Key Vault: Key Vault Secrets Officer role
- Storage: Storage Blob Data Owner role
- App Insights: Monitoring Metrics Publisher role

## Benefits

1. **No Secrets to Manage**: No connection strings, access keys, or service principal credentials
2. **Automatic Rotation**: Tokens are short-lived and automatically refreshed
3. **Audit Trail**: All authentication attempts are logged in Azure AD
4. **Least Privilege**: Use Azure RBAC for fine-grained access control
5. **Works Everywhere**: Same code works in dev (with Azure CLI) and production (with Workload Identity)

## Identity Federation for Non-Azure Agents

External agents (running outside Azure) can also join this identity system using federated credentials. Here's how:

### GitHub Actions Example

```yaml
name: Call MCP Server
on: [push]

permissions:
  id-token: write  # Required for OIDC token
  contents: read

jobs:
  call-mcp:
    runs-on: ubuntu-latest
    steps:
      - name: Azure Login via OIDC
        uses: azure/login@v1
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
      
      - name: Call MCP Server
        run: |
          # Get token for Key Vault
          TOKEN=$(az account get-access-token --resource https://vault.azure.net --query accessToken -o tsv)
          
          # Use token to access Key Vault via MCP
          curl -X POST https://your-apim.azure-api.net/mcp/message \
            -H "Authorization: Bearer $TOKEN" \
            -H "Content-Type: application/json" \
            -d '{"method":"tools/call","params":{"name":"get_secret","arguments":{"secret_name":"api-key"}}}'
```

### AWS EKS Workload Identity

AWS EKS can also use OIDC federation with Azure:

1. Create federated credential in Azure:
```bash
az identity federated-credential create \
  --name eks-federation \
  --identity-name mcp-server-identity \
  --resource-group $RESOURCE_GROUP \
  --issuer https://oidc.eks.region.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE \
  --subject system:serviceaccount:default:mcp-server \
  --audience sts.amazonaws.com
```

2. Configure EKS service account to use Azure Workload Identity SDK

### Google Cloud GKE

Similar setup with GKE Workload Identity:

```bash
az identity federated-credential create \
  --name gke-federation \
  --identity-name mcp-server-identity \
  --resource-group $RESOURCE_GROUP \
  --issuer https://container.googleapis.com/v1/projects/PROJECT_ID/locations/REGION/clusters/CLUSTER_NAME \
  --subject system:serviceaccount:default:mcp-server \
  --audience api://AzureADTokenExchange
```

## Troubleshooting

### Error: "DefaultAzureCredential failed to retrieve a token"

Check:
1. Pod has `azure.workload.identity/use: "true"` label
2. Service account has correct client-id annotation
3. Federated credential exists and matches service account

```bash
# Check federated credentials
az identity federated-credential list \
  --identity-name <managed-identity-name> \
  --resource-group $RESOURCE_GROUP
```

### Error: "AADSTS70021: No matching federated identity record found"

The federated credential subject doesn't match the service account. Verify:

```bash
kubectl get sa mcp-server-sa -n mcp-server -o yaml
# Subject should be: system:serviceaccount:mcp-server:mcp-server-sa
```

### Tokens not refreshing

The workload identity webhook should inject environment variables. Check:

```bash
kubectl get mutatingwebhookconfigurations
# Look for: azure-wi-webhook-mutating-webhook-configuration
```

## Best Practices

1. **Use Managed Identities**: Always prefer Workload Identity over service principals
2. **Separate Identities**: Use different managed identities for different workloads
3. **Least Privilege**: Grant only necessary permissions via RBAC
4. **Monitor Usage**: Enable diagnostic logs for managed identities
5. **Rotate Federation**: Periodically review and update federated credentials

## References

- [AKS Workload Identity Overview](https://learn.microsoft.com/azure/aks/workload-identity-overview)
- [Azure Identity SDK for Python](https://learn.microsoft.com/python/api/overview/azure/identity-readme)
- [Federated Identity Credentials](https://learn.microsoft.com/entra/workload-id/workload-identity-federation)
- [OIDC in AKS](https://learn.microsoft.com/azure/aks/use-oidc-issuer)
