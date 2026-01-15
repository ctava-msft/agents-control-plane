@description('Cosmos DB account name')
param cosmosAccountName string

@description('Principal ID to grant access')
param principalId string

@description('Role definition ID (built-in or custom)')
// Cosmos DB Built-in Data Contributor role
param roleDefinitionId string = '00000000-0000-0000-0000-000000000002'

resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' existing = {
  name: cosmosAccountName
}

resource cosmosRoleAssignment 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-05-15' = {
  parent: cosmosAccount
  name: guid(cosmosAccount.id, principalId, roleDefinitionId)
  properties: {
    roleDefinitionId: '${cosmosAccount.id}/sqlRoleDefinitions/${roleDefinitionId}'
    principalId: principalId
    scope: cosmosAccount.id
  }
}

output roleAssignmentId string = cosmosRoleAssignment.id
