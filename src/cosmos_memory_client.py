"""
Cosmos DB Memory Client - Long-term memory storage for agent threads and tool traces
"""

import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
from azure.identity import DefaultAzureCredential
from azure.cosmos import CosmosClient, PartitionKey
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from opentelemetry import trace

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class CosmosMemoryClient:
    """
    Client for storing and retrieving agent memory from Cosmos DB:
    - Agent conversation threads
    - Tool execution traces
    - Long-term memory for multi-turn conversations
    """

    def __init__(
        self,
        endpoint: str,
        database_name: str,
        threads_container: str = "threads",
        traces_container: str = "tool-traces",
        credential: Optional[DefaultAzureCredential] = None,
    ):
        """
        Initialize Cosmos DB memory client
        
        Args:
            endpoint: Cosmos DB account endpoint
            database_name: Name of the database
            threads_container: Name of threads container
            traces_container: Name of traces container
            credential: Azure credential for authentication
        """
        self.endpoint = endpoint
        self.database_name = database_name
        self.threads_container_name = threads_container
        self.traces_container_name = traces_container
        self.credential = credential or DefaultAzureCredential()
        
        # Initialize Cosmos client
        self.client = CosmosClient(
            url=endpoint,
            credential=self.credential,
        )
        
        self.database = self.client.get_database_client(database_name)
        self.threads_container = self.database.get_container_client(threads_container)
        self.traces_container = self.database.get_container_client(traces_container)
        
        logger.info(f"Initialized Cosmos memory client for database: {database_name}")

    async def store_thread_message(
        self,
        agent_id: str,
        thread_id: str,
        message: Dict[str, Any],
    ) -> bool:
        """
        Store a message in an agent conversation thread
        
        Args:
            agent_id: Unique agent identifier (partition key)
            thread_id: Conversation thread identifier
            message: Message content and metadata
            
        Returns:
            bool: True if storage succeeded
        """
        with tracer.start_as_current_span("cosmos.store_thread_message") as span:
            span.set_attribute("agent_id", agent_id)
            span.set_attribute("thread_id", thread_id)
            
            try:
                # Try to get existing thread
                try:
                    thread_doc = self.threads_container.read_item(
                        item=thread_id,
                        partition_key=agent_id,
                    )
                except CosmosResourceNotFoundError:
                    # Create new thread
                    thread_doc = {
                        "id": thread_id,
                        "agentId": agent_id,
                        "createdAt": datetime.utcnow().isoformat(),
                        "messages": [],
                    }
                
                # Add message to thread
                message_with_timestamp = {
                    **message,
                    "timestamp": datetime.utcnow().isoformat(),
                }
                thread_doc["messages"].append(message_with_timestamp)
                thread_doc["lastUpdated"] = datetime.utcnow().isoformat()
                
                # Upsert thread document
                self.threads_container.upsert_item(thread_doc)
                
                span.set_attribute("messages.count", len(thread_doc["messages"]))
                logger.info(f"Stored message in thread {thread_id} for agent {agent_id}")
                return True
                
            except Exception as e:
                logger.error(f"Error storing thread message: {e}")
                span.set_attribute("error", str(e))
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                return False

    async def get_thread_history(
        self,
        agent_id: str,
        thread_id: str,
        limit: Optional[int] = None,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieve conversation history for a thread
        
        Args:
            agent_id: Unique agent identifier
            thread_id: Conversation thread identifier
            limit: Optional limit on number of messages to return (most recent)
            
        Returns:
            List of messages or None if thread not found
        """
        with tracer.start_as_current_span("cosmos.get_thread_history") as span:
            span.set_attribute("agent_id", agent_id)
            span.set_attribute("thread_id", thread_id)
            
            try:
                thread_doc = self.threads_container.read_item(
                    item=thread_id,
                    partition_key=agent_id,
                )
                
                messages = thread_doc.get("messages", [])
                
                if limit:
                    messages = messages[-limit:]
                
                span.set_attribute("messages.count", len(messages))
                logger.info(f"Retrieved {len(messages)} messages from thread {thread_id}")
                return messages
                
            except CosmosResourceNotFoundError:
                logger.info(f"Thread {thread_id} not found for agent {agent_id}")
                return None
            except Exception as e:
                logger.error(f"Error retrieving thread history: {e}")
                span.set_attribute("error", str(e))
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                return None

    async def store_tool_trace(
        self,
        tool_name: str,
        trace_id: str,
        execution_data: Dict[str, Any],
    ) -> bool:
        """
        Store a tool execution trace
        
        Args:
            tool_name: Name of the tool (partition key)
            trace_id: Unique trace identifier
            execution_data: Tool execution details
            
        Returns:
            bool: True if storage succeeded
        """
        with tracer.start_as_current_span("cosmos.store_tool_trace") as span:
            span.set_attribute("tool_name", tool_name)
            span.set_attribute("trace_id", trace_id)
            
            try:
                trace_doc = {
                    "id": trace_id,
                    "toolName": tool_name,
                    "timestamp": datetime.utcnow().isoformat(),
                    **execution_data,
                }
                
                self.traces_container.create_item(trace_doc)
                
                logger.info(f"Stored tool trace {trace_id} for tool {tool_name}")
                span.set_attribute("trace.stored", True)
                return True
                
            except Exception as e:
                logger.error(f"Error storing tool trace: {e}")
                span.set_attribute("error", str(e))
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                return False

    async def query_tool_traces(
        self,
        tool_name: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Query recent tool execution traces
        
        Args:
            tool_name: Name of the tool
            limit: Number of traces to return
            
        Returns:
            List of tool traces
        """
        with tracer.start_as_current_span("cosmos.query_tool_traces") as span:
            span.set_attribute("tool_name", tool_name)
            span.set_attribute("limit", limit)
            
            try:
                query = """
                SELECT TOP @limit *
                FROM c
                WHERE c.toolName = @toolName
                ORDER BY c.timestamp DESC
                """
                
                parameters = [
                    {"name": "@limit", "value": limit},
                    {"name": "@toolName", "value": tool_name},
                ]
                
                traces = list(self.traces_container.query_items(
                    query=query,
                    parameters=parameters,
                    partition_key=tool_name,
                ))
                
                span.set_attribute("traces.count", len(traces))
                logger.info(f"Retrieved {len(traces)} traces for tool {tool_name}")
                return traces
                
            except Exception as e:
                logger.error(f"Error querying tool traces: {e}")
                span.set_attribute("error", str(e))
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                return []


def create_cosmos_memory_client() -> Optional[CosmosMemoryClient]:
    """
    Factory function to create Cosmos memory client from environment variables
    
    Returns:
        CosmosMemoryClient instance or None if not configured
    """
    endpoint = os.getenv("COSMOS_DB_ENDPOINT")
    database_name = os.getenv("COSMOS_DB_DATABASE_NAME", "agents-memory")
    threads_container = os.getenv("COSMOS_DB_THREADS_CONTAINER", "threads")
    traces_container = os.getenv("COSMOS_DB_TRACES_CONTAINER", "tool-traces")
    
    if not endpoint:
        logger.warning("COSMOS_DB_ENDPOINT not configured - memory features disabled")
        return None
    
    try:
        client = CosmosMemoryClient(
            endpoint=endpoint,
            database_name=database_name,
            threads_container=threads_container,
            traces_container=traces_container,
        )
        
        return client
    except Exception as e:
        logger.error(f"Failed to create Cosmos memory client: {e}")
        return None
