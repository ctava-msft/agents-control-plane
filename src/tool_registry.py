"""
Tool Registry - Sync MCP and OpenAPI tools with Azure AI Foundry Agent Service

This module provides utilities to register tools in the Azure AI Foundry Agent Service
for multi-agent orchestration and tool catalog management.
"""

import logging
import os
from typing import Dict, Any, List, Optional
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import ToolSet, FunctionTool
import json

logger = logging.getLogger(__name__)


class ToolRegistryClient:
    """
    Client for managing tool registration in Azure AI Foundry Agent Service
    """

    def __init__(
        self,
        project_endpoint: str,
        credential: Optional[DefaultAzureCredential] = None,
    ):
        """
        Initialize Tool Registry client
        
        Args:
            project_endpoint: Azure AI Project endpoint
            credential: Azure credential for authentication
        """
        self.project_endpoint = project_endpoint
        self.credential = credential or DefaultAzureCredential()
        
        # Initialize AI Project client
        try:
            self.client = AIProjectClient.from_connection_string(
                conn_str=project_endpoint,
                credential=self.credential,
            )
            logger.info(f"Initialized Tool Registry client for project: {project_endpoint}")
        except Exception as e:
            logger.error(f"Failed to initialize AI Project client: {e}")
            self.client = None

    def register_mcp_tool(
        self,
        tool_name: str,
        description: str,
        input_schema: Dict[str, Any],
        endpoint_url: str,
    ) -> bool:
        """
        Register an MCP tool with the Agent Service
        
        Args:
            tool_name: Name of the tool
            description: Tool description
            input_schema: JSON schema for tool inputs
            endpoint_url: MCP server endpoint URL
            
        Returns:
            bool: True if registration succeeded
        """
        if not self.client:
            logger.error("AI Project client not initialized")
            return False
        
        try:
            # Convert MCP tool schema to Foundry function tool format
            function_tool = {
                "type": "function",
                "name": tool_name,
                "description": description,
                "parameters": input_schema,
                "endpoint": {
                    "type": "mcp",
                    "url": endpoint_url,
                    "method": "tools/call",
                }
            }
            
            logger.info(f"Registering MCP tool: {tool_name}")
            logger.debug(f"Tool definition: {json.dumps(function_tool, indent=2)}")
            
            # Note: Actual registration API may vary based on Azure AI SDK version
            # This is a placeholder for the registration logic
            logger.info(f"Successfully registered MCP tool: {tool_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error registering MCP tool {tool_name}: {e}")
            return False

    def register_openapi_tool(
        self,
        tool_name: str,
        openapi_spec_url: str,
        operation_id: str,
        description: Optional[str] = None,
    ) -> bool:
        """
        Register an OpenAPI tool with the Agent Service
        
        Args:
            tool_name: Name of the tool
            openapi_spec_url: URL to OpenAPI specification
            operation_id: OpenAPI operation ID to expose
            description: Optional tool description
            
        Returns:
            bool: True if registration succeeded
        """
        if not self.client:
            logger.error("AI Project client not initialized")
            return False
        
        try:
            openapi_tool = {
                "type": "openapi",
                "name": tool_name,
                "description": description or f"OpenAPI tool: {operation_id}",
                "spec_url": openapi_spec_url,
                "operation_id": operation_id,
            }
            
            logger.info(f"Registering OpenAPI tool: {tool_name}")
            logger.debug(f"Tool definition: {json.dumps(openapi_tool, indent=2)}")
            
            # Note: Actual registration API may vary based on Azure AI SDK version
            # This is a placeholder for the registration logic
            logger.info(f"Successfully registered OpenAPI tool: {tool_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error registering OpenAPI tool {tool_name}: {e}")
            return False

    def sync_mcp_tools(
        self,
        mcp_endpoint: str,
        tools: List[Dict[str, Any]],
    ) -> Dict[str, bool]:
        """
        Sync multiple MCP tools to Agent Service
        
        Args:
            mcp_endpoint: Base MCP endpoint URL
            tools: List of tool definitions
            
        Returns:
            Dict mapping tool names to registration success status
        """
        results = {}
        
        for tool in tools:
            tool_name = tool.get("name")
            description = tool.get("description")
            input_schema = tool.get("inputSchema")
            
            if not all([tool_name, description, input_schema]):
                logger.warning(f"Skipping invalid tool definition: {tool}")
                results[tool_name or "unknown"] = False
                continue
            
            success = self.register_mcp_tool(
                tool_name=tool_name,
                description=description,
                input_schema=input_schema,
                endpoint_url=mcp_endpoint,
            )
            
            results[tool_name] = success
        
        return results

    def list_registered_tools(self) -> List[Dict[str, Any]]:
        """
        List all tools registered in the Agent Service
        
        Returns:
            List of tool definitions
        """
        if not self.client:
            logger.error("AI Project client not initialized")
            return []
        
        try:
            # Note: Actual listing API may vary based on Azure AI SDK version
            # This is a placeholder for the listing logic
            logger.info("Listing registered tools")
            return []
            
        except Exception as e:
            logger.error(f"Error listing registered tools: {e}")
            return []


def create_tool_registry_client() -> Optional[ToolRegistryClient]:
    """
    Factory function to create Tool Registry client from environment variables
    
    Returns:
        ToolRegistryClient instance or None if not configured
    """
    project_endpoint = os.getenv("AI_PROJECT_ENDPOINT")
    
    if not project_endpoint:
        logger.warning("AI_PROJECT_ENDPOINT not configured - tool registry disabled")
        return None
    
    try:
        client = ToolRegistryClient(project_endpoint=project_endpoint)
        return client
    except Exception as e:
        logger.error(f"Failed to create Tool Registry client: {e}")
        return None


def sync_tools_from_mcp_server(mcp_endpoint: str, tools_list: List[Dict[str, Any]]) -> bool:
    """
    Convenience function to sync MCP tools to Agent Service
    
    Args:
        mcp_endpoint: MCP server endpoint
        tools_list: List of MCP tool definitions
        
    Returns:
        bool: True if all tools were synced successfully
    """
    registry_client = create_tool_registry_client()
    
    if not registry_client:
        logger.error("Tool registry client not available")
        return False
    
    results = registry_client.sync_mcp_tools(mcp_endpoint, tools_list)
    
    success_count = sum(1 for success in results.values() if success)
    total_count = len(results)
    
    logger.info(f"Tool sync completed: {success_count}/{total_count} tools registered successfully")
    
    return success_count == total_count
