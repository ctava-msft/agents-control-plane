# Azure Key Vault Integration

This document explains how Azure Key Vault is integrated into the MCP server for secure secrets management.

## Overview

The MCP server uses Azure Key Vault to store and retrieve sensitive credentials, API keys, and other secrets without embedding them in configuration files or environment variables.

## Architecture

```
MCP Server Pod (AKS)
    ↓ (Workload Identity)
Azure Managed Identity
    ↓ (RBAC: Key Vault Secrets Officer)
Azure Key Vault
    └── Secrets (encrypted at rest)
```

## Features

1. **Managed Identity Authentication**: Uses Azure Workload Identity for passwordless authentication
2. **RBAC Authorization**: Fine-grained access control using Azure RBAC
3. **Private Endpoints**: Optional private endpoint for network isolation
4. **Audit Logging**: All Key Vault access is logged to Azure Monitor

## MCP Tools for Key Vault

### get_secret

Retrieve a secret from Azure Key Vault.

**Input Schema:**
```json
{
  "secret_name": "my-api-key"
}
```

**Response:**
```json
{
  "content": [{
    "type": "text",
    "text": "secret-value-here"
  }],
  "isError": false
}
```

### set_secret

Store a secret in Azure Key Vault (requires Key Vault Secrets Officer role).

**Input Schema:**
```json
{
  "secret_name": "my-api-key",
  "secret_value": "super-secret-value"
}
```

**Response:**
```json
{
  "content": [{
    "type": "text",
    "text": "Secret 'my-api-key' stored successfully in Key Vault"
  }],
  "isError": false
}
```

## Configuration

### Infrastructure Setup

The Key Vault is deployed via Bicep in `infra/main.bicep`:

```bicep
module keyVault './core/keyvault/keyvault.bicep' = {
  name: 'keyVault'
  scope: rg
  params: {
    keyVaultName: '${abbrs.keyVaultVaults}${resourceToken}'
    location: location
    tags: tags
    enableRbacAuthorization: true
    publicNetworkAccess: vnetEnabled ? 'Disabled' : 'Enabled'
  }
}
```

### RBAC Role Assignment

The MCP server workload identity is granted the Key Vault Secrets Officer role:

```bicep
var keyVaultSecretsOfficerRoleId = 'b86a8fe4-44ce-4948-aee5-eccb2c155cd7'
module keyVaultRoleAssignmentMcp './core/keyvault/keyvault-access.bicep' = {
  name: 'keyVaultRoleAssignmentMcp'
  scope: rg
  params: {
    keyVaultName: keyVault.outputs.keyVaultName
    roleDefinitionID: keyVaultSecretsOfficerRoleId
    principalID: mcpUserAssignedIdentity.outputs.identityPrincipalId
  }
}
```

### Environment Variables

Set the following environment variable in your Kubernetes deployment:

```yaml
env:
- name: AZURE_KEY_VAULT_URL
  value: "https://kv-xxxxx.vault.azure.net/"
- name: AZURE_CLIENT_ID
  value: "managed-identity-client-id"
```

## Private Endpoint (Optional)

For enhanced security, enable private endpoints:

1. Set `vnetEnabled=true` in your deployment
2. The Key Vault will be accessible only from within the VNet
3. DNS resolution is handled via Private DNS Zone

```bicep
module keyVaultPrivateEndpoint './core/keyvault/keyvault-privateendpoint.bicep' = if (vnetEnabled) {
  name: 'keyVaultPrivateEndpoint'
  scope: rg
  params: {
    keyVaultName: keyVault.outputs.keyVaultName
    location: location
    tags: tags
    virtualNetworkName: serviceVirtualNetworkName
    subnetName: serviceVirtualNetworkPrivateEndpointSubnetName
  }
}
```

## Security Best Practices

1. **Use Managed Identity**: Never use access keys or connection strings
2. **Least Privilege**: Grant only necessary permissions (Secrets User vs Secrets Officer)
3. **Enable Purge Protection**: Prevents accidental deletion of secrets
4. **Soft Delete**: Allows recovery of deleted secrets within retention period
5. **Audit Logs**: Monitor Key Vault access via Azure Monitor
6. **Private Endpoints**: Use when requiring network isolation

## Access Logs

Key Vault access logs are automatically sent to Log Analytics workspace. View them with:

```kusto
AzureDiagnostics
| where ResourceType == "VAULTS"
| where OperationName == "SecretGet" or OperationName == "SecretSet"
| project TimeGenerated, CallerIPAddress, identity_claim_oid_g, OperationName, ResultType
| order by TimeGenerated desc
```

## Troubleshooting

### "Access Denied" errors

Check RBAC role assignment:
```bash
az role assignment list --scope /subscriptions/{sub-id}/resourceGroups/{rg}/providers/Microsoft.KeyVault/vaults/{vault-name}
```

### Managed Identity not working

Verify workload identity is properly configured:
```bash
kubectl describe serviceaccount mcp-server-sa -n mcp-server
kubectl get pod -n mcp-server -o yaml | grep azure.workload.identity
```

### Key Vault not accessible

Check network rules:
```bash
az keyvault show --name {vault-name} --query "properties.networkAcls"
```

## Example Usage

Store a Foundry API key:

```bash
# Using MCP Inspector or AI agent
{
  "method": "tools/call",
  "params": {
    "name": "set_secret",
    "arguments": {
      "secret_name": "foundry-api-key",
      "secret_value": "sk-xxxxxxxxxxxxx"
    }
  }
}
```

Retrieve it later:

```bash
{
  "method": "tools/call",
  "params": {
    "name": "get_secret",
    "arguments": {
      "secret_name": "foundry-api-key"
    }
  }
}
```

## References

- [Azure Key Vault Documentation](https://learn.microsoft.com/azure/key-vault/)
- [Workload Identity for AKS](https://learn.microsoft.com/azure/aks/workload-identity-overview)
- [Key Vault RBAC Guide](https://learn.microsoft.com/azure/key-vault/general/rbac-guide)
