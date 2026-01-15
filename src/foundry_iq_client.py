"""
Foundry IQ Client - Integration with Azure AI Foundry for agentic search and retrieval
"""

import logging
import os
from typing import Dict, Any, Optional, List
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
)
from opentelemetry import trace

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class FoundryIQClient:
    """
    Client for Azure AI Foundry IQ operations including:
    - Agentic search and retrieval
    - Document indexing
    - Vector search capabilities
    
    Note: FabricIQ data alignment can be configured through Azure AI Foundry portal
    for integration with Microsoft Fabric data sources.
    """

    def __init__(
        self,
        search_endpoint: str,
        index_name: str = "agent-knowledge-base",
        credential: Optional[DefaultAzureCredential] = None,
    ):
        """
        Initialize Foundry IQ client
        
        Args:
            search_endpoint: Azure AI Search service endpoint
            index_name: Name of the search index
            credential: Azure credential for authentication
        """
        self.search_endpoint = search_endpoint
        self.index_name = index_name
        self.credential = credential or DefaultAzureCredential()
        
        # Initialize search clients
        self.search_client = SearchClient(
            endpoint=search_endpoint,
            index_name=index_name,
            credential=self.credential,
        )
        
        self.index_client = SearchIndexClient(
            endpoint=search_endpoint,
            credential=self.credential,
        )
        
        logger.info(f"Initialized Foundry IQ client for endpoint: {search_endpoint}")

    def ensure_index_exists(self) -> bool:
        """
        Ensure the search index exists with proper schema for agent operations
        
        Returns:
            bool: True if index exists or was created successfully
        """
        with tracer.start_as_current_span("foundry_iq.ensure_index") as span:
            try:
                # Check if index already exists
                existing_indexes = [idx.name for idx in self.index_client.list_indexes()]
                if self.index_name in existing_indexes:
                    logger.info(f"Index '{self.index_name}' already exists")
                    span.set_attribute("index.exists", True)
                    return True
                
                # Define index schema for agent knowledge base
                fields = [
                    SimpleField(name="id", type=SearchFieldDataType.String, key=True),
                    SearchableField(name="content", type=SearchFieldDataType.String, analyzer_name="en.microsoft"),
                    SearchableField(name="title", type=SearchFieldDataType.String),
                    SimpleField(name="category", type=SearchFieldDataType.String, filterable=True, facetable=True),
                    SimpleField(name="source", type=SearchFieldDataType.String, filterable=True),
                    SimpleField(name="timestamp", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
                    SearchableField(name="metadata", type=SearchFieldDataType.String),
                ]
                
                # Create index
                index = SearchIndex(name=self.index_name, fields=fields)
                self.index_client.create_index(index)
                
                logger.info(f"Created index '{self.index_name}' successfully")
                span.set_attribute("index.created", True)
                return True
                
            except Exception as e:
                logger.error(f"Error ensuring index exists: {e}")
                span.set_attribute("error", str(e))
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                return False

    async def search_knowledge_base(
        self,
        query: str,
        top: int = 5,
        filters: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Perform agentic search against the knowledge base
        
        Args:
            query: Natural language search query
            top: Number of results to return
            filters: Optional OData filter expression
            
        Returns:
            List of search results with content and metadata
        """
        with tracer.start_as_current_span("foundry_iq.search") as span:
            span.set_attribute("query", query)
            span.set_attribute("top", top)
            
            try:
                results = self.search_client.search(
                    search_text=query,
                    top=top,
                    filter=filters,
                    include_total_count=True,
                )
                
                search_results = []
                for result in results:
                    search_results.append({
                        "id": result.get("id"),
                        "title": result.get("title"),
                        "content": result.get("content"),
                        "category": result.get("category"),
                        "source": result.get("source"),
                        "score": result.get("@search.score"),
                    })
                
                span.set_attribute("results.count", len(search_results))
                logger.info(f"Found {len(search_results)} results for query: {query}")
                
                return search_results
                
            except Exception as e:
                logger.error(f"Error performing search: {e}")
                span.set_attribute("error", str(e))
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                raise

    async def index_document(
        self,
        doc_id: str,
        content: str,
        title: str,
        category: str = "general",
        source: str = "agent",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Index a document into the knowledge base
        
        Args:
            doc_id: Unique document identifier
            content: Document content
            title: Document title
            category: Document category
            source: Document source
            metadata: Additional metadata
            
        Returns:
            bool: True if indexing succeeded
        """
        with tracer.start_as_current_span("foundry_iq.index_document") as span:
            span.set_attribute("document.id", doc_id)
            span.set_attribute("document.category", category)
            
            try:
                from datetime import datetime
                
                document = {
                    "id": doc_id,
                    "content": content,
                    "title": title,
                    "category": category,
                    "source": source,
                    "timestamp": datetime.utcnow().isoformat(),
                    "metadata": str(metadata) if metadata else "",
                }
                
                result = self.search_client.upload_documents(documents=[document])
                
                success = result[0].succeeded if result else False
                span.set_attribute("index.success", success)
                
                if success:
                    logger.info(f"Successfully indexed document: {doc_id}")
                else:
                    logger.error(f"Failed to index document: {doc_id}")
                
                return success
                
            except Exception as e:
                logger.error(f"Error indexing document: {e}")
                span.set_attribute("error", str(e))
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                return False


def create_foundry_iq_client() -> Optional[FoundryIQClient]:
    """
    Factory function to create Foundry IQ client from environment variables
    
    Returns:
        FoundryIQClient instance or None if not configured
    """
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    index_name = os.getenv("AZURE_SEARCH_INDEX_NAME", "agent-knowledge-base")
    
    if not search_endpoint:
        logger.warning("AZURE_SEARCH_ENDPOINT not configured - Foundry IQ features disabled")
        return None
    
    try:
        client = FoundryIQClient(
            search_endpoint=search_endpoint,
            index_name=index_name,
        )
        
        # Ensure index exists
        client.ensure_index_exists()
        
        return client
    except Exception as e:
        logger.error(f"Failed to create Foundry IQ client: {e}")
        return None
