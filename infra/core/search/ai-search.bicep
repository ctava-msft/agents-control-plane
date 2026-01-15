@description('Azure AI Search service name')
param searchServiceName string

@description('Location for the search service')
param location string = resourceGroup().location

@description('Tags for the resource')
param tags object = {}

@description('SKU for the search service')
@allowed(['basic', 'standard', 'standard2', 'standard3', 'storage_optimized_l1', 'storage_optimized_l2', 'free'])
param sku string = 'basic'

@description('Number of replicas')
@minValue(1)
@maxValue(12)
param replicaCount int = 1

@description('Number of partitions')
@allowed([1, 2, 3, 4, 6, 12])
param partitionCount int = 1

@description('Public network access setting')
@allowed(['enabled', 'disabled'])
param publicNetworkAccess string = 'enabled'

@description('Disable local authentication (use Entra ID only)')
param disableLocalAuth bool = true

resource searchService 'Microsoft.Search/searchServices@2024-06-01-preview' = {
  name: searchServiceName
  location: location
  tags: tags
  sku: {
    name: sku
  }
  properties: {
    replicaCount: replicaCount
    partitionCount: partitionCount
    hostingMode: 'default'
    publicNetworkAccess: publicNetworkAccess
    disableLocalAuth: disableLocalAuth
    authOptions: {
      aadOrApiKey: {
        aadAuthFailureMode: 'http401WithBearerChallenge'
      }
    }
  }
  identity: {
    type: 'SystemAssigned'
  }
}

output searchServiceName string = searchService.name
output searchServiceEndpoint string = 'https://${searchService.name}.search.windows.net'
output searchServiceId string = searchService.id
output searchServicePrincipalId string = searchService.identity.principalId
