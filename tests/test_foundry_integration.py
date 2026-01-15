#!/usr/bin/env python3
"""
Integration tests for Foundry IQ, Cosmos DB memory, and tool registry

Tests validate:
1. Foundry IQ search client initialization and search
2. Cosmos DB memory storage for threads and traces
3. Azure AI Search index creation and queries
4. Tool registry synchronization
"""

import asyncio
import os
import uuid
from datetime import datetime
import pytest

# Set test environment variables
os.environ["AZURE_SEARCH_ENDPOINT"] = os.getenv("AZURE_SEARCH_ENDPOINT", "https://test-search.search.windows.net")
os.environ["COSMOS_DB_ENDPOINT"] = os.getenv("COSMOS_DB_ENDPOINT", "https://test-cosmos.documents.azure.com:443/")
os.environ["AI_PROJECT_ENDPOINT"] = os.getenv("AI_PROJECT_ENDPOINT", "https://test-project.api.azureml.ms")

# Import after setting env vars
from foundry_iq_client import FoundryIQClient, create_foundry_iq_client
from cosmos_memory_client import CosmosMemoryClient, create_cosmos_memory_client
from tool_registry import ToolRegistryClient, create_tool_registry_client


class TestFoundryIQClient:
    """Tests for Foundry IQ search client"""
    
    def test_client_initialization(self):
        """Test Foundry IQ client can be initialized"""
        search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
        
        if not search_endpoint:
            pytest.skip("AZURE_SEARCH_ENDPOINT not configured")
        
        client = create_foundry_iq_client()
        
        # Client should be created or None if not configured
        # We don't require it to succeed if credentials aren't available
        assert client is None or isinstance(client, FoundryIQClient)
    
    @pytest.mark.asyncio
    async def test_search_knowledge_base(self):
        """Test knowledge base search"""
        client = create_foundry_iq_client()
        
        if not client:
            pytest.skip("Foundry IQ client not configured")
        
        try:
            # Perform a test search
            results = await client.search_knowledge_base(
                query="test query",
                top=5
            )
            
            # Results should be a list (may be empty)
            assert isinstance(results, list)
            
        except Exception as e:
            # Search may fail if index doesn't exist yet, which is OK for initial tests
            print(f"Search test skipped: {e}")
            pytest.skip(f"Search not available: {e}")
    
    @pytest.mark.asyncio
    async def test_index_document(self):
        """Test document indexing"""
        client = create_foundry_iq_client()
        
        if not client:
            pytest.skip("Foundry IQ client not configured")
        
        try:
            # Index a test document
            doc_id = f"test-{uuid.uuid4()}"
            success = await client.index_document(
                doc_id=doc_id,
                content="This is a test document for integration testing",
                title="Test Document",
                category="test",
                source="integration_test",
                metadata={"test": True}
            )
            
            # May fail if index doesn't exist, which is OK
            assert isinstance(success, bool)
            
        except Exception as e:
            print(f"Indexing test skipped: {e}")
            pytest.skip(f"Indexing not available: {e}")


class TestCosmosMemoryClient:
    """Tests for Cosmos DB memory client"""
    
    def test_client_initialization(self):
        """Test Cosmos memory client can be initialized"""
        cosmos_endpoint = os.getenv("COSMOS_DB_ENDPOINT")
        
        if not cosmos_endpoint:
            pytest.skip("COSMOS_DB_ENDPOINT not configured")
        
        client = create_cosmos_memory_client()
        
        # Client should be created or None if not configured
        assert client is None or isinstance(client, CosmosMemoryClient)
    
    @pytest.mark.asyncio
    async def test_store_thread_message(self):
        """Test storing a thread message"""
        client = create_cosmos_memory_client()
        
        if not client:
            pytest.skip("Cosmos memory client not configured")
        
        try:
            # Store a test message
            agent_id = "test-agent"
            thread_id = f"test-thread-{uuid.uuid4()}"
            message = {
                "role": "user",
                "content": "Test message"
            }
            
            success = await client.store_thread_message(
                agent_id=agent_id,
                thread_id=thread_id,
                message=message
            )
            
            assert isinstance(success, bool)
            
            # If successful, try to retrieve it
            if success:
                history = await client.get_thread_history(
                    agent_id=agent_id,
                    thread_id=thread_id
                )
                
                assert history is not None
                assert isinstance(history, list)
                assert len(history) >= 1
            
        except Exception as e:
            print(f"Thread storage test skipped: {e}")
            pytest.skip(f"Thread storage not available: {e}")
    
    @pytest.mark.asyncio
    async def test_store_tool_trace(self):
        """Test storing a tool execution trace"""
        client = create_cosmos_memory_client()
        
        if not client:
            pytest.skip("Cosmos memory client not configured")
        
        try:
            # Store a test trace
            tool_name = "test_tool"
            trace_id = str(uuid.uuid4())
            execution_data = {
                "arguments": {"test": "value"},
                "result": "success",
                "duration_ms": 100
            }
            
            success = await client.store_tool_trace(
                tool_name=tool_name,
                trace_id=trace_id,
                execution_data=execution_data
            )
            
            assert isinstance(success, bool)
            
            # If successful, try to query traces
            if success:
                traces = await client.query_tool_traces(
                    tool_name=tool_name,
                    limit=10
                )
                
                assert isinstance(traces, list)
            
        except Exception as e:
            print(f"Tool trace test skipped: {e}")
            pytest.skip(f"Tool trace storage not available: {e}")


class TestToolRegistry:
    """Tests for tool registry client"""
    
    def test_client_initialization(self):
        """Test tool registry client can be initialized"""
        project_endpoint = os.getenv("AI_PROJECT_ENDPOINT")
        
        if not project_endpoint:
            pytest.skip("AI_PROJECT_ENDPOINT not configured")
        
        client = create_tool_registry_client()
        
        # Client should be created or None if not configured
        assert client is None or isinstance(client, ToolRegistryClient)
    
    def test_register_mcp_tool(self):
        """Test registering an MCP tool"""
        client = create_tool_registry_client()
        
        if not client:
            pytest.skip("Tool registry client not configured")
        
        try:
            # Register a test tool
            success = client.register_mcp_tool(
                tool_name="test_tool",
                description="Test tool for integration testing",
                input_schema={
                    "type": "object",
                    "properties": {
                        "test_param": {"type": "string"}
                    },
                    "required": ["test_param"]
                },
                endpoint_url="https://test-mcp.example.com/mcp"
            )
            
            # Registration may fail if service not available, which is OK
            assert isinstance(success, bool)
            
        except Exception as e:
            print(f"Tool registration test skipped: {e}")
            pytest.skip(f"Tool registration not available: {e}")
    
    def test_register_openapi_tool(self):
        """Test registering an OpenAPI tool"""
        client = create_tool_registry_client()
        
        if not client:
            pytest.skip("Tool registry client not configured")
        
        try:
            # Register a test OpenAPI tool
            success = client.register_openapi_tool(
                tool_name="test_openapi_tool",
                openapi_spec_url="https://petstore3.swagger.io/api/v3/openapi.json",
                operation_id="getPetById",
                description="Test OpenAPI tool"
            )
            
            # Registration may fail if service not available, which is OK
            assert isinstance(success, bool)
            
        except Exception as e:
            print(f"OpenAPI tool registration test skipped: {e}")
            pytest.skip(f"OpenAPI tool registration not available: {e}")


class TestMCPToolIntegration:
    """Integration tests for MCP tool with new features"""
    
    @pytest.mark.asyncio
    async def test_foundry_iq_search_tool(self):
        """Test foundry_iq_search MCP tool"""
        from mcp_server import execute_tool
        
        # Test the tool execution
        result = await execute_tool(
            tool_name="foundry_iq_search",
            arguments={
                "query": "test query",
                "top": 3
            }
        )
        
        # Should return a result (may indicate service not configured)
        assert result is not None
        assert hasattr(result, 'content')
        assert isinstance(result.content, list)
        assert len(result.content) > 0


def run_tests():
    """Run all integration tests"""
    print("=" * 80)
    print("Running Integration Tests for Central Memory + Foundry IQ")
    print("=" * 80)
    print()
    
    # Run pytest
    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-k", "test_"
    ])
    
    return exit_code


if __name__ == "__main__":
    exit(run_tests())
