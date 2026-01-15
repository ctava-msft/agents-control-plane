# Azure AI Search Sample Queries

This document provides sample queries and usage patterns for the Azure AI Search integration with Foundry IQ.

## Overview

The Foundry IQ integration uses Azure AI Search to provide:
- Full-text search across indexed documents
- Filtering by category, source, and date
- Semantic search capabilities
- ACL-based access control

## Index Schema

The default `agent-knowledge-base` index has the following schema:

| Field | Type | Searchable | Filterable | Sortable | Description |
|-------|------|------------|------------|----------|-------------|
| `id` | String | No | No | No | Unique document identifier (key) |
| `content` | String | Yes | No | No | Full document content |
| `title` | String | Yes | No | No | Document title |
| `category` | String | No | Yes | No | Document category |
| `source` | String | No | Yes | No | Document source |
| `timestamp` | DateTimeOffset | No | Yes | Yes | Document timestamp |
| `metadata` | String | Yes | No | No | Additional metadata (JSON string) |

## Sample Queries

### 1. Simple Text Search

Search for documents containing specific keywords:

```python
from foundry_iq_client import create_foundry_iq_client

client = create_foundry_iq_client()

# Search for "deployment"
results = await client.search_knowledge_base(
    query="deployment best practices",
    top=10
)

for result in results:
    print(f"Title: {result['title']}")
    print(f"Score: {result['score']}")
    print(f"Content: {result['content'][:200]}...")
    print()
```

### 2. Filtered Search by Category

Search within a specific category:

```python
# Search in "security" category only
results = await client.search_knowledge_base(
    query="authentication methods",
    top=5,
    filters="category eq 'security'"
)
```

### 3. Filtered Search by Source

Search documents from a specific source:

```python
# Search in documentation only
results = await client.search_knowledge_base(
    query="API reference",
    top=10,
    filters="source eq 'documentation'"
)
```

### 4. Combined Filters

Use multiple filters with OData syntax:

```python
# Search in security documentation
results = await client.search_knowledge_base(
    query="encryption",
    top=5,
    filters="category eq 'security' and source eq 'documentation'"
)
```

### 5. Date Range Filtering

Search for recent documents:

```python
from datetime import datetime, timedelta

# Documents from the last 7 days
seven_days_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()

results = await client.search_knowledge_base(
    query="latest updates",
    top=10,
    filters=f"timestamp ge {seven_days_ago}"
)
```

### 6. Using the MCP Tool

Search via the `foundry_iq_search` MCP tool:

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "foundry_iq_search",
    "arguments": {
      "query": "How do I configure authentication?",
      "top": 5,
      "category": "security"
    }
  },
  "id": 1
}
```

### 7. Indexing Documents

Add documents to the knowledge base:

```python
from foundry_iq_client import create_foundry_iq_client

client = create_foundry_iq_client()

# Index a document
success = await client.index_document(
    doc_id="doc-001",
    content="""
    Azure Kubernetes Service (AKS) provides a managed Kubernetes cluster.
    To deploy applications, use kubectl or Helm charts. For production
    deployments, enable RBAC and network policies.
    """,
    title="AKS Deployment Guide",
    category="deployment",
    source="documentation",
    metadata={
        "author": "Platform Team",
        "tags": ["kubernetes", "aks", "deployment"]
    }
)

if success:
    print("Document indexed successfully")
```

### 8. Batch Indexing

Index multiple documents at once:

```python
documents = [
    {
        "doc_id": "security-001",
        "title": "OAuth 2.0 Setup",
        "content": "Configure OAuth 2.0 authentication...",
        "category": "security"
    },
    {
        "doc_id": "api-001",
        "title": "API Reference",
        "content": "REST API endpoints and usage...",
        "category": "api"
    }
]

for doc in documents:
    await client.index_document(
        doc_id=doc["doc_id"],
        content=doc["content"],
        title=doc["title"],
        category=doc["category"],
        source="documentation"
    )
```

## OData Filter Syntax

Azure AI Search supports OData filter expressions:

### Comparison Operators

- `eq` - equals
- `ne` - not equals
- `gt` - greater than
- `ge` - greater than or equal
- `lt` - less than
- `le` - less than or equal

### Logical Operators

- `and` - logical AND
- `or` - logical OR
- `not` - logical NOT

### Examples

```python
# Category is 'security' OR 'api'
filters="category eq 'security' or category eq 'api'"

# Not in 'deprecated' category
filters="not (category eq 'deprecated')"

# Recent security documents
filters="category eq 'security' and timestamp ge 2024-01-01T00:00:00Z"

# Multiple sources
filters="source eq 'documentation' or source eq 'blog'"
```

## Common Query Patterns

### Pattern 1: Find Related Documentation

```python
def find_related_docs(topic: str, limit: int = 5):
    """Find documentation related to a topic"""
    return await client.search_knowledge_base(
        query=topic,
        top=limit,
        filters="source eq 'documentation'"
    )
```

### Pattern 2: Search Code Examples

```python
def find_code_examples(language: str, topic: str):
    """Find code examples in a specific language"""
    return await client.search_knowledge_base(
        query=f"{topic} {language}",
        top=10,
        filters="category eq 'code-samples'"
    )
```

### Pattern 3: Get Recent Updates

```python
from datetime import datetime, timedelta

def get_recent_updates(days: int = 7):
    """Get documents updated in the last N days"""
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    return await client.search_knowledge_base(
        query="*",
        top=20,
        filters=f"timestamp ge {cutoff}"
    )
```

### Pattern 4: Category Browse

```python
def browse_category(category: str, page: int = 1, page_size: int = 10):
    """Browse all documents in a category"""
    return await client.search_knowledge_base(
        query="*",
        top=page_size,
        filters=f"category eq '{category}'"
    )
```

## Performance Tips

1. **Use Filters**: Filters are more efficient than text search alone
2. **Limit Results**: Use the `top` parameter to limit results
3. **Index Strategically**: Only index fields that need to be searchable
4. **Use Categories**: Organize documents into categories for better filtering
5. **Batch Operations**: Index multiple documents in batches when possible

## Monitoring Queries

All search queries are traced in Application Insights:

```kusto
// View Foundry IQ search operations
traces
| where operation_Name == "foundry_iq.search"
| extend query = tostring(customDimensions.query)
| extend results_count = toint(customDimensions["results.count"])
| project timestamp, query, results_count, duration
| order by timestamp desc
```

## Access Control (ACLs)

Documents in the search index can be secured with ACLs:

1. Add a `security_filter` field to indexed documents
2. Include user/group identifiers in the filter
3. Apply filters based on authenticated user context

```python
# Example with ACL field
await client.index_document(
    doc_id="secure-doc-001",
    content="Confidential information...",
    title="Secure Document",
    category="confidential",
    source="internal",
    metadata={
        "security_filter": "group:engineering,group:leadership"
    }
)

# Query with ACL filter
user_groups = ["engineering"]
results = await client.search_knowledge_base(
    query="confidential data",
    filters=f"security_filter eq 'group:{user_groups[0]}'"
)
```

## Troubleshooting

### No Results Returned

1. Check if index exists: `client.ensure_index_exists()`
2. Verify documents are indexed
3. Try broader search terms
4. Remove filters temporarily to diagnose

### Search Too Slow

1. Reduce `top` parameter
2. Add more specific filters
3. Consider using semantic search (if enabled)
4. Check index statistics in Azure portal

### Permission Errors

1. Verify managed identity has "Search Index Data Contributor" role
2. Check AZURE_SEARCH_ENDPOINT is correct
3. Ensure network connectivity to search service

## See Also

- [Azure AI Search Documentation](https://learn.microsoft.com/azure/search/)
- [OData Filter Syntax](https://learn.microsoft.com/azure/search/search-query-odata-filter)
- [Search Index Design](https://learn.microsoft.com/azure/search/search-what-is-an-index)
- [Tool Registry Documentation](TOOL_REGISTRY.md)
