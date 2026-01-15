@description('Azure AI Hub name')
param aiHubName string

@description('AI Project name for Agent Service')
param aiProjectName string

@description('Location for the AI resources')
param location string = resourceGroup().location

@description('Tags for the resource')
param tags object = {}

@description('Key Vault resource ID for secrets')
param keyVaultId string

@description('Storage account resource ID')
param storageAccountId string

@description('Application Insights resource ID')
param applicationInsightsId string

@description('Container Registry resource ID')
param containerRegistryId string

// AI Hub - central governance for AI projects
resource aiHub 'Microsoft.MachineLearningServices/workspaces@2024-04-01' = {
  name: aiHubName
  location: location
  tags: tags
  kind: 'Hub'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    friendlyName: aiHubName
    description: 'Azure AI Foundry Hub for Agent Orchestration'
    keyVault: keyVaultId
    storageAccount: storageAccountId
    applicationInsights: applicationInsightsId
    containerRegistry: containerRegistryId
    publicNetworkAccess: 'Enabled'
  }
  sku: {
    name: 'Basic'
    tier: 'Basic'
  }
}

// AI Project - workspace for agent development and deployment
resource aiProject 'Microsoft.MachineLearningServices/workspaces@2024-04-01' = {
  name: aiProjectName
  location: location
  tags: tags
  kind: 'Project'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    friendlyName: aiProjectName
    description: 'Azure AI Foundry Project for multi-agent orchestration and tool registry'
    hubResourceId: aiHub.id
    publicNetworkAccess: 'Enabled'
  }
  sku: {
    name: 'Basic'
    tier: 'Basic'
  }
}

output aiHubName string = aiHub.name
output aiHubId string = aiHub.id
output aiHubPrincipalId string = aiHub.identity.principalId
output aiProjectName string = aiProject.name
output aiProjectId string = aiProject.id
output aiProjectPrincipalId string = aiProject.identity.principalId
