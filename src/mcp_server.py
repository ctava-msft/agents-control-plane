"""
FastAPI MCP Server - Replacement for Azure Functions
Implements Model Context Protocol (MCP) with SSE support
Enhanced with:
- Azure Key Vault integration for secrets management
- OpenTelemetry distributed tracing and logging
- Agent365 human-in-the-loop approval workflow
"""

import json
import logging
import asyncio
import uuid
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse, JSONResponse
from azure.storage.blob import BlobServiceClient
from azure.storage.queue import QueueServiceClient
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.core.exceptions import ResourceNotFoundError
import os

# OpenTelemetry imports
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from azure.monitor.opentelemetry.exporter import (
    AzureMonitorTraceExporter,
    AzureMonitorMetricExporter,
    AzureMonitorLogExporter
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s - trace_id=%(otelTraceID)s span_id=%(otelSpanID)s'
)
logger = logging.getLogger(__name__)

# Initialize OpenTelemetry
def setup_opentelemetry():
    """Setup OpenTelemetry with Azure Monitor"""
    connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "")
    
    if connection_string:
        # Setup tracing
        trace_exporter = AzureMonitorTraceExporter(connection_string=connection_string)
        tracer_provider = TracerProvider()
        tracer_provider.add_span_processor(BatchSpanProcessor(trace_exporter))
        trace.set_tracer_provider(tracer_provider)
        
        # Setup metrics
        metric_exporter = AzureMonitorMetricExporter(connection_string=connection_string)
        metric_reader = PeriodicExportingMetricReader(metric_exporter)
        meter_provider = MeterProvider(metric_readers=[metric_reader])
        metrics.set_meter_provider(meter_provider)
        
        # Instrument logging
        LoggingInstrumentor().instrument()
        
        logger.info("OpenTelemetry configured with Azure Monitor")
    else:
        logger.warning("APPLICATIONINSIGHTS_CONNECTION_STRING not set - telemetry disabled")

setup_opentelemetry()

# Initialize FastAPI app
app = FastAPI(
    title="MCP Server",
    description="Model Context Protocol Server for AI Agents with Azure integration",
    version="2.0.0"
)

# Instrument FastAPI with OpenTelemetry
FastAPIInstrumentor.instrument_app(app)

# Get tracer and meter for custom telemetry
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

# Custom metrics
tool_execution_counter = meter.create_counter(
    "mcp.tool.executions",
    description="Number of MCP tool executions",
    unit="1"
)
tool_execution_duration = meter.create_histogram(
    "mcp.tool.duration",
    description="Duration of MCP tool executions",
    unit="ms"
)

# Azure configuration
STORAGE_ACCOUNT_URL = os.getenv("AZURE_STORAGE_ACCOUNT_URL", "")
STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
KEY_VAULT_URL = os.getenv("AZURE_KEY_VAULT_URL", "")

# Initialize Azure clients
credential = DefaultAzureCredential()

# Key Vault client
if KEY_VAULT_URL:
    try:
        key_vault_client = SecretClient(vault_url=KEY_VAULT_URL, credential=credential)
        logger.info(f"Key Vault client initialized: {KEY_VAULT_URL}")
    except Exception as e:
        logger.warning(f"Failed to initialize Key Vault client: {e}")
        key_vault_client = None
else:
    logger.warning("AZURE_KEY_VAULT_URL not set - Key Vault features disabled")
    key_vault_client = None

# Storage client
if STORAGE_CONNECTION_STRING:
    blob_service_client = BlobServiceClient.from_connection_string(STORAGE_CONNECTION_STRING)
    queue_service_client = QueueServiceClient.from_connection_string(STORAGE_CONNECTION_STRING)
elif STORAGE_ACCOUNT_URL:
    blob_service_client = BlobServiceClient(account_url=STORAGE_ACCOUNT_URL, credential=credential)
    # Extract account name from URL for queue service
    account_name = STORAGE_ACCOUNT_URL.split("//")[1].split(".")[0]
    queue_account_url = f"https://{account_name}.queue.core.windows.net"
    queue_service_client = QueueServiceClient(account_url=queue_account_url, credential=credential)
    logger.info("Storage clients initialized with Managed Identity")
else:
    logger.warning("No storage configuration found - storage features disabled")
    blob_service_client = None
    queue_service_client = None

SNIPPETS_CONTAINER = "snippets"
APPROVALS_QUEUE = "agent365-approvals"

# In-memory session storage (replace with Redis for production)
sessions: Dict[str, Dict[str, Any]] = {}


@dataclass
class MCPTool:
    """MCP Tool definition"""
    name: str
    description: str
    inputSchema: Dict[str, Any]


@dataclass
class MCPToolResult:
    """MCP Tool execution result"""
    content: list
    isError: bool = False


# Define MCP tools
TOOLS = [
    MCPTool(
        name="hello_mcp",
        description="Hello world MCP tool.",
        inputSchema={
            "type": "object",
            "properties": {},
            "required": []
        }
    ),
    MCPTool(
        name="get_snippet",
        description="Retrieve a snippet by name from Azure Blob Storage.",
        inputSchema={
            "type": "object",
            "properties": {
                "snippetname": {
                    "type": "string",
                    "description": "The name of the snippet to retrieve"
                }
            },
            "required": ["snippetname"]
        }
    ),
    MCPTool(
        name="save_snippet",
        description="Save a snippet with a name to Azure Blob Storage.",
        inputSchema={
            "type": "object",
            "properties": {
                "snippetname": {
                    "type": "string",
                    "description": "The name of the snippet"
                },
                "snippet": {
                    "type": "string",
                    "description": "The content of the snippet"
                }
            },
            "required": ["snippetname", "snippet"]
        }
    ),
    MCPTool(
        name="get_secret",
        description="Retrieve a secret from Azure Key Vault. Requires Key Vault access.",
        inputSchema={
            "type": "object",
            "properties": {
                "secret_name": {
                    "type": "string",
                    "description": "The name of the secret to retrieve from Key Vault"
                }
            },
            "required": ["secret_name"]
        }
    ),
    MCPTool(
        name="set_secret",
        description="Store a secret in Azure Key Vault. Requires Key Vault Secrets Officer role.",
        inputSchema={
            "type": "object",
            "properties": {
                "secret_name": {
                    "type": "string",
                    "description": "The name of the secret to store"
                },
                "secret_value": {
                    "type": "string",
                    "description": "The value of the secret to store"
                }
            },
            "required": ["secret_name", "secret_value"]
        }
    ),
    MCPTool(
        name="request_approval",
        description="Agent365: Request human approval for a sensitive action. Returns an approval request ID.",
        inputSchema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Description of the action requiring approval"
                },
                "context": {
                    "type": "string",
                    "description": "Additional context or details about the action"
                },
                "requester": {
                    "type": "string",
                    "description": "Identifier of the agent or user requesting approval"
                }
            },
            "required": ["action", "requester"]
        }
    ),
    MCPTool(
        name="check_approval_status",
        description="Agent365: Check the status of a pending approval request.",
        inputSchema={
            "type": "object",
            "properties": {
                "approval_id": {
                    "type": "string",
                    "description": "The approval request ID to check"
                }
            },
            "required": ["approval_id"]
        }
    )
]


async def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> MCPToolResult:
    """Execute an MCP tool with OpenTelemetry tracing"""
    with tracer.start_as_current_span(f"execute_tool.{tool_name}") as span:
        span.set_attribute("tool.name", tool_name)
        span.set_attribute("tool.arguments", json.dumps(arguments))
        start_time = datetime.utcnow()
        
        try:
            if tool_name == "hello_mcp":
                result = MCPToolResult(
                    content=[{
                        "type": "text",
                        "text": "Hello I am MCPTool!"
                    }]
                )
            
            elif tool_name == "get_snippet":
                snippet_name = arguments.get("snippetname")
                if not snippet_name:
                    return MCPToolResult(
                        content=[{"type": "text", "text": "No snippet name provided"}],
                        isError=True
                    )
                
                if not blob_service_client:
                    return MCPToolResult(
                        content=[{"type": "text", "text": "Storage not configured"}],
                        isError=True
                    )
                
                try:
                    blob_client = blob_service_client.get_blob_client(
                        container=SNIPPETS_CONTAINER,
                        blob=f"{snippet_name}.json"
                    )
                    blob_data = blob_client.download_blob().readall()
                    snippet_content = blob_data.decode('utf-8')
                    
                    result = MCPToolResult(
                        content=[{
                            "type": "text",
                            "text": snippet_content
                        }]
                    )
                except Exception as e:
                    logger.error(f"Error retrieving snippet: {e}")
                    return MCPToolResult(
                        content=[{"type": "text", "text": f"Error retrieving snippet: {str(e)}"}],
                        isError=True
                    )
            
            elif tool_name == "save_snippet":
                snippet_name = arguments.get("snippetname")
                snippet_content = arguments.get("snippet")
                
                if not snippet_name:
                    return MCPToolResult(
                        content=[{"type": "text", "text": "No snippet name provided"}],
                        isError=True
                    )
                
                if not snippet_content:
                    return MCPToolResult(
                        content=[{"type": "text", "text": "No snippet content provided"}],
                        isError=True
                    )
                
                if not blob_service_client:
                    return MCPToolResult(
                        content=[{"type": "text", "text": "Storage not configured"}],
                        isError=True
                    )
                
                try:
                    blob_client = blob_service_client.get_blob_client(
                        container=SNIPPETS_CONTAINER,
                        blob=f"{snippet_name}.json"
                    )
                    blob_client.upload_blob(snippet_content.encode('utf-8'), overwrite=True)
                    
                    result = MCPToolResult(
                        content=[{
                            "type": "text",
                            "text": f"Snippet '{snippet_name}' saved successfully"
                        }]
                    )
                except Exception as e:
                    logger.error(f"Error saving snippet: {e}")
                    return MCPToolResult(
                        content=[{"type": "text", "text": f"Error saving snippet: {str(e)}"}],
                        isError=True
                    )
            
            elif tool_name == "get_secret":
                secret_name = arguments.get("secret_name")
                if not secret_name:
                    return MCPToolResult(
                        content=[{"type": "text", "text": "No secret name provided"}],
                        isError=True
                    )
                
                if not key_vault_client:
                    return MCPToolResult(
                        content=[{"type": "text", "text": "Key Vault not configured"}],
                        isError=True
                    )
                
                try:
                    secret = key_vault_client.get_secret(secret_name)
                    logger.info(f"Retrieved secret: {secret_name}")
                    span.set_attribute("keyvault.secret.name", secret_name)
                    
                    result = MCPToolResult(
                        content=[{
                            "type": "text",
                            "text": secret.value
                        }]
                    )
                except ResourceNotFoundError:
                    logger.warning(f"Secret not found: {secret_name}")
                    return MCPToolResult(
                        content=[{"type": "text", "text": f"Secret '{secret_name}' not found in Key Vault"}],
                        isError=True
                    )
                except Exception as e:
                    logger.error(f"Error retrieving secret: {e}")
                    return MCPToolResult(
                        content=[{"type": "text", "text": f"Error retrieving secret: {str(e)}"}],
                        isError=True
                    )
            
            elif tool_name == "set_secret":
                secret_name = arguments.get("secret_name")
                secret_value = arguments.get("secret_value")
                
                if not secret_name or not secret_value:
                    return MCPToolResult(
                        content=[{"type": "text", "text": "Secret name and value are required"}],
                        isError=True
                    )
                
                if not key_vault_client:
                    return MCPToolResult(
                        content=[{"type": "text", "text": "Key Vault not configured"}],
                        isError=True
                    )
                
                try:
                    key_vault_client.set_secret(secret_name, secret_value)
                    logger.info(f"Stored secret: {secret_name}")
                    span.set_attribute("keyvault.secret.name", secret_name)
                    
                    result = MCPToolResult(
                        content=[{
                            "type": "text",
                            "text": f"Secret '{secret_name}' stored successfully in Key Vault"
                        }]
                    )
                except Exception as e:
                    logger.error(f"Error storing secret: {e}")
                    return MCPToolResult(
                        content=[{"type": "text", "text": f"Error storing secret: {str(e)}"}],
                        isError=True
                    )
            
            elif tool_name == "request_approval":
                action = arguments.get("action")
                context = arguments.get("context", "")
                requester = arguments.get("requester")
                
                if not action or not requester:
                    return MCPToolResult(
                        content=[{"type": "text", "text": "Action and requester are required"}],
                        isError=True
                    )
                
                if not queue_service_client:
                    return MCPToolResult(
                        content=[{"type": "text", "text": "Queue service not configured"}],
                        isError=True
                    )
                
                try:
                    # Create approval request
                    approval_id = str(uuid.uuid4())
                    approval_request = {
                        "approval_id": approval_id,
                        "action": action,
                        "context": context,
                        "requester": requester,
                        "status": "pending",
                        "created_at": datetime.utcnow().isoformat()
                    }
                    
                    # Send to approval queue
                    queue_client = queue_service_client.get_queue_client(APPROVALS_QUEUE)
                    
                    # Create queue if it doesn't exist
                    try:
                        queue_client.create_queue()
                    except Exception:
                        pass  # Queue might already exist
                    
                    queue_client.send_message(json.dumps(approval_request))
                    
                    logger.info(f"Approval request created: {approval_id}")
                    span.set_attribute("approval.id", approval_id)
                    span.set_attribute("approval.requester", requester)
                    
                    result = MCPToolResult(
                        content=[{
                            "type": "text",
                            "text": f"Approval request submitted. ID: {approval_id}\nStatus: pending\nAction: {action}"
                        }]
                    )
                except Exception as e:
                    logger.error(f"Error creating approval request: {e}")
                    return MCPToolResult(
                        content=[{"type": "text", "text": f"Error creating approval request: {str(e)}"}],
                        isError=True
                    )
            
            elif tool_name == "check_approval_status":
                approval_id = arguments.get("approval_id")
                
                if not approval_id:
                    return MCPToolResult(
                        content=[{"type": "text", "text": "Approval ID is required"}],
                        isError=True
                    )
                
                # For demo purposes, return pending status
                # In production, this would query a database or check queue messages
                result = MCPToolResult(
                    content=[{
                        "type": "text",
                        "text": f"Approval ID: {approval_id}\nStatus: pending\n\nNote: This is a demo implementation. In production, integrate with approval management system."
                    }]
                )
            
            else:
                return MCPToolResult(
                    content=[{"type": "text", "text": f"Unknown tool: {tool_name}"}],
                    isError=True
                )
            
            # Record metrics
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            tool_execution_counter.add(1, {"tool.name": tool_name, "status": "success"})
            tool_execution_duration.record(duration_ms, {"tool.name": tool_name})
            span.set_attribute("tool.duration_ms", duration_ms)
            span.set_attribute("tool.status", "success")
            
            return result
        
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
            tool_execution_counter.add(1, {"tool.name": tool_name, "status": "error"})
            span.set_attribute("tool.status", "error")
            span.set_attribute("tool.error", str(e))
            span.record_exception(e)
            
            return MCPToolResult(
                content=[{"type": "text", "text": f"Error: {str(e)}"}],
                isError=True
            )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.get("/runtime/webhooks/mcp/sse")
async def mcp_sse_endpoint(request: Request):
    """
    SSE endpoint for MCP protocol
    Establishes a long-lived connection for server-sent events
    """
    session_id = str(uuid.uuid4())
    logger.info(f"New SSE session established: {session_id}")
    
    # Store session
    sessions[session_id] = {
        "created_at": datetime.utcnow().isoformat(),
        "message_queue": asyncio.Queue()
    }
    
    async def event_generator():
        try:
            # Send initial connection event with message endpoint
            message_url = f"message?sessionId={session_id}"
            yield f"data: {message_url}\n\n"
            
            # Keep connection alive and send any queued messages
            while True:
                if session_id not in sessions:
                    break
                
                try:
                    # Wait for messages with timeout
                    message = await asyncio.wait_for(
                        sessions[session_id]["message_queue"].get(),
                        timeout=30.0
                    )
                    yield f"data: {json.dumps(message)}\n\n"
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield ": keepalive\n\n"
                    
        except asyncio.CancelledError:
            logger.info(f"SSE connection cancelled for session {session_id}")
        finally:
            # Cleanup session
            if session_id in sessions:
                del sessions[session_id]
            logger.info(f"SSE session closed: {session_id}")
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/runtime/webhooks/mcp/message")
async def mcp_message_endpoint(request: Request):
    """
    Message endpoint for MCP protocol
    Handles JSON-RPC 2.0 requests with distributed tracing
    """
    with tracer.start_as_current_span("mcp_message_endpoint") as span:
        try:
            body = await request.json()
            logger.info(f"Received MCP message: {json.dumps(body)[:200]}")
            
            jsonrpc_version = body.get("jsonrpc")
            method = body.get("method")
            params = body.get("params", {})
            request_id = body.get("id")
            
            span.set_attribute("jsonrpc.version", jsonrpc_version)
            span.set_attribute("jsonrpc.method", method)
            span.set_attribute("jsonrpc.id", str(request_id))
            
            if jsonrpc_version != "2.0":
                return JSONResponse(
                    status_code=400,
                    content={
                        "jsonrpc": "2.0",
                        "error": {"code": -32600, "message": "Invalid Request"},
                        "id": request_id
                    }
                )
            
            # Handle initialize
            if method == "initialize":
                response = {
                    "jsonrpc": "2.0",
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {}
                        },
                        "serverInfo": {
                            "name": "mcp-server",
                            "version": "2.0.0"
                        }
                    },
                    "id": request_id
                }
                return JSONResponse(content=response)
            
            # Handle tools/list
            elif method == "tools/list":
                tools_list = [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": tool.inputSchema
                    }
                    for tool in TOOLS
                ]
                
                response = {
                    "jsonrpc": "2.0",
                    "result": {
                        "tools": tools_list
                    },
                    "id": request_id
                }
                return JSONResponse(content=response)
            
            # Handle tools/call
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                
                span.set_attribute("tool.name", tool_name)
                
                # Execute the tool
                result = await execute_tool(tool_name, arguments)
                
                response = {
                    "jsonrpc": "2.0",
                    "result": asdict(result),
                    "id": request_id
                }
                return JSONResponse(content=response)
            
            else:
                return JSONResponse(
                    status_code=400,
                    content={
                        "jsonrpc": "2.0",
                        "error": {"code": -32601, "message": f"Method not found: {method}"},
                        "id": request_id
                    }
                )
        
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            span.record_exception(e)
            span.set_attribute("error", True)
            
            return JSONResponse(
                status_code=500,
                content={
                    "jsonrpc": "2.0",
                    "error": {"code": -32603, "message": f"Internal error: {str(e)}"},
                    "id": body.get("id") if 'body' in locals() else None
                }
            )


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "MCP Server",
        "version": "1.0.0",
        "endpoints": {
            "sse": "/runtime/webhooks/mcp/sse",
            "message": "/runtime/webhooks/mcp/message",
            "health": "/health"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
