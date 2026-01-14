@description('Name of the Key Vault')
param keyVaultName string

@description('Role definition ID for RBAC')
param roleDefinitionID string

@description('Principal ID to grant access')
param principalID string

@description('Principal type (ServicePrincipal, User, Group)')
param principalType string = 'ServicePrincipal'

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

resource roleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, principalID, roleDefinitionID)
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitionID)
    principalId: principalID
    principalType: principalType
  }
}

output roleAssignmentId string = roleAssignment.id
