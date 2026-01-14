# Unified Observability with Azure Monitor, Application Insights, and Sentinel

This document describes the comprehensive observability solution for the MCP server, including distributed tracing, metrics, logging, and security monitoring.

## Overview

The MCP server implements unified telemetry using OpenTelemetry, with all signals (traces, metrics, logs) exported to Azure Monitor and Log Analytics. This enables:

- **Distributed Tracing**: Track requests from APIM → MCP → Foundry IQ
- **Metrics Collection**: Custom business metrics for tool usage
- **Structured Logging**: Correlated logs with trace context
- **Security Monitoring**: Integration with Microsoft Sentinel for threat detection

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  APIM (API Gateway)                                  │
│  └── Diagnostic Logs → Log Analytics                │
└────────────────┬────────────────────────────────────┘
                 │ HTTP Request (trace-id propagated)
                 ↓
┌─────────────────────────────────────────────────────┐
│  MCP Server (FastAPI + OpenTelemetry)               │
│  ├── Traces (spans for each operation)              │
│  ├── Metrics (tool execution counts, duration)      │
│  └── Logs (structured with trace context)           │
└────────────────┬────────────────────────────────────┘
                 │ OpenTelemetry Protocol
                 ↓
┌─────────────────────────────────────────────────────┐
│  Azure Monitor Exporter                              │
│  ├── Trace Exporter → Application Insights          │
│  ├── Metric Exporter → Application Insights         │
│  └── Log Exporter → Log Analytics                   │
└────────────────┬────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────┐
│  Azure Monitor & Log Analytics                       │
│  ├── Application Insights (traces, metrics)         │
│  ├── Log Analytics Workspace (logs)                 │
│  └── Workbooks & Dashboards                         │
└────────────────┬────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────┐
│  Microsoft Sentinel (Security Analytics)             │
│  ├── Threat Detection Rules                         │
│  ├── Incident Management                            │
│  └── Security Dashboards                            │
└─────────────────────────────────────────────────────┘
```

## Distributed Tracing

### Trace Propagation

The system uses W3C Trace Context for distributed tracing:

1. **APIM** generates initial `traceparent` header
2. **MCP Server** continues the trace with child spans
3. **Foundry IQ** (optional) can participate in the same trace

Example trace hierarchy:
```
span: apim.request (trace-id: abc123)
  └─ span: mcp.message.endpoint (parent: apim.request)
      └─ span: execute_tool.save_snippet (parent: mcp.message.endpoint)
          └─ span: azure.storage.blob.upload (parent: execute_tool.save_snippet)
```

### View Traces in Application Insights

Navigate to Application Insights → Transaction Search:

**Query for MCP tool executions:**
```kusto
traces
| where operation_Name startswith "execute_tool"
| project timestamp, operation_Name, message, customDimensions
| order by timestamp desc
```

**Query for end-to-end request flow:**
```kusto
requests
| where url contains "mcp/message"
| join kind=inner (dependencies) on operation_Id
| project timestamp, name, url, resultCode, duration, dependency_Name = name1
| order by timestamp desc
```

**Find slow requests:**
```kusto
requests
| where url contains "mcp"
| where duration > 1000  // milliseconds
| project timestamp, url, duration, operation_Id
| order by duration desc
```

## Custom Metrics

The MCP server exports custom metrics for monitoring:

### Tool Execution Counter

Counts the number of tool executions by tool name and status:

```python
tool_execution_counter.add(1, {
    "tool.name": tool_name,
    "status": "success"  # or "error"
})
```

**Query in Application Insights:**
```kusto
customMetrics
| where name == "mcp.tool.executions"
| summarize count() by tostring(customDimensions.["tool.name"]), tostring(customDimensions.status)
| render barchart
```

### Tool Execution Duration

Histogram of tool execution times:

```python
tool_execution_duration.record(duration_ms, {
    "tool.name": tool_name
})
```

**Query for average duration by tool:**
```kusto
customMetrics
| where name == "mcp.tool.duration"
| summarize avg(value), percentile(value, 95) by tostring(customDimensions.["tool.name"])
| render timechart
```

## Structured Logging

All logs include trace context for correlation:

```python
logger.info(
    "Tool executed successfully",
    extra={
        "tool_name": tool_name,
        "duration_ms": duration_ms,
        "user_id": user_id
    }
)
```

Log format includes trace and span IDs:
```
2024-01-14 00:15:44 - mcp_server - INFO - Tool executed successfully - trace_id=abc123 span_id=def456
```

**Query correlated logs:**
```kusto
traces
| where customDimensions.SpanId == "def456"
| project timestamp, message, severityLevel, customDimensions
| order by timestamp asc
```

## Monitoring Dashboards

### Pre-built Queries

**Tool Usage Report:**
```kusto
customMetrics
| where name == "mcp.tool.executions"
| summarize executions = sum(value) by bin(timestamp, 1h), tool = tostring(customDimensions.["tool.name"])
| render timechart
```

**Error Rate:**
```kusto
let total = customMetrics
| where name == "mcp.tool.executions"
| summarize total = sum(value);
let errors = customMetrics
| where name == "mcp.tool.executions"
| where customDimensions.status == "error"
| summarize errors = sum(value);
total | join (errors) on $left.timestamp == $right.timestamp
| extend error_rate = errors * 100.0 / total
| render timechart
```

**Latency Percentiles:**
```kusto
customMetrics
| where name == "mcp.tool.duration"
| summarize 
    p50 = percentile(value, 50),
    p95 = percentile(value, 95),
    p99 = percentile(value, 99)
    by bin(timestamp, 5m)
| render timechart
```

### Create Azure Workbook

1. Navigate to Application Insights → Workbooks
2. Click "New" → "Advanced Editor"
3. Use the provided KQL queries above
4. Save as "MCP Server Monitoring"

## APIM Integration

APIM diagnostic logs are sent to Log Analytics:

**View APIM requests:**
```kusto
ApiManagementGatewayLogs
| where OperationId == "mcp-api"
| project TimeGenerated, Method, Url, BackendUrl, ResponseCode, ResponseSize, DurationMs
| order by TimeGenerated desc
```

**Correlate APIM with MCP traces:**
```kusto
ApiManagementGatewayLogs
| extend trace_id = tostring(parse_json(RequestHeaders)["traceparent"])
| join kind=inner (
    requests
    | extend trace_id = operation_Id
) on trace_id
| project TimeGenerated, Url, BackendUrl, ResponseCode, duration
```

## Microsoft Sentinel Integration

### Enable Sentinel

1. Navigate to Log Analytics workspace
2. Click "Microsoft Sentinel" → "Add"
3. Select the workspace
4. Enable data connectors: Azure Activity, Azure Key Vault

### Security Analytics Rules

**Detect Multiple Failed Key Vault Access:**
```kusto
AzureDiagnostics
| where ResourceType == "VAULTS"
| where ResultType == "Forbidden" or ResultType == "Unauthorized"
| summarize failed_attempts = count() by identity_claim_oid_g, bin(TimeGenerated, 5m)
| where failed_attempts > 5
| extend Severity = "High"
```

**Detect Unusual Tool Usage Pattern:**
```kusto
customMetrics
| where name == "mcp.tool.executions"
| summarize executions = sum(value) by tool = tostring(customDimensions.["tool.name"]), bin(timestamp, 1h)
| join kind=inner (
    customMetrics
    | where name == "mcp.tool.executions"
    | summarize baseline = avg(value) by tool = tostring(customDimensions.["tool.name"])
) on tool
| where executions > baseline * 3  // 3x baseline
| extend Severity = "Medium"
```

**Detect Agent365 Approval Bypass Attempts:**
```kusto
traces
| where message contains "approval" and message contains "bypass"
| extend Severity = "Critical"
| project TimeGenerated, message, customDimensions
```

### Create Sentinel Workbook

Example dashboard for security monitoring:

1. **Key Vault Access Map**: Who accessed what secrets
2. **Failed Authentication**: Chart of failed auth attempts
3. **Anomalous Behavior**: Unusual tool execution patterns
4. **Approval Workflow**: Pending approvals and resolution time

## Alerting

### Create Alerts in Azure Monitor

**High Error Rate Alert:**
```kusto
customMetrics
| where name == "mcp.tool.executions"
| where customDimensions.status == "error"
| summarize error_count = sum(value) by bin(timestamp, 5m)
| where error_count > 10
```

Alert configuration:
- Frequency: 5 minutes
- Threshold: > 10 errors
- Action: Email + Teams notification

**Slow Response Time Alert:**
```kusto
requests
| where url contains "mcp"
| summarize avg_duration = avg(duration) by bin(timestamp, 5m)
| where avg_duration > 2000  // milliseconds
```

**Key Vault Access Denied Alert:**
```kusto
AzureDiagnostics
| where ResourceType == "VAULTS"
| where ResultType == "Forbidden"
| summarize count() by bin(TimeGenerated, 5m)
| where count_ > 3
```

## OpenTelemetry Configuration

The MCP server uses OpenTelemetry SDK with Azure Monitor exporters:

```python
from azure.monitor.opentelemetry.exporter import (
    AzureMonitorTraceExporter,
    AzureMonitorMetricExporter,
)
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Setup tracing
connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
trace_exporter = AzureMonitorTraceExporter(connection_string=connection_string)
tracer_provider = TracerProvider()
tracer_provider.add_span_processor(BatchSpanProcessor(trace_exporter))
trace.set_tracer_provider(tracer_provider)

# Setup metrics
metric_exporter = AzureMonitorMetricExporter(connection_string=connection_string)
metric_reader = PeriodicExportingMetricReader(metric_exporter)
meter_provider = MeterProvider(metric_readers=[metric_reader])
metrics.set_meter_provider(meter_provider)
```

### Automatic Instrumentation

FastAPI is automatically instrumented:

```python
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

FastAPIInstrumentor.instrument_app(app)
```

This captures:
- HTTP request/response details
- Route parameters
- Query strings
- Response codes
- Latencies

## Best Practices

1. **Use Correlation IDs**: Always propagate trace context across service boundaries
2. **Structured Logging**: Use JSON or key-value pairs for log messages
3. **Sample Wisely**: Use adaptive sampling in high-traffic scenarios
4. **Set Spans Attributes**: Add relevant business context to spans
5. **Monitor Cardinality**: Avoid high-cardinality dimensions in metrics
6. **Alert on SLOs**: Define and alert on Service Level Objectives

## Performance Considerations

### Sampling

For high-traffic production deployments, enable sampling:

```python
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

# Sample 10% of traces
sampler = TraceIdRatioBased(0.1)
tracer_provider = TracerProvider(sampler=sampler)
```

### Batch Processing

Use batch processing for better performance:

```python
# Traces
BatchSpanProcessor(
    trace_exporter,
    max_queue_size=2048,
    schedule_delay_millis=5000,
    max_export_batch_size=512
)

# Metrics
PeriodicExportingMetricReader(
    metric_exporter,
    export_interval_millis=60000  # Export every 60 seconds
)
```

## Troubleshooting

### No Telemetry Showing Up

1. Check Application Insights connection string:
   ```bash
   kubectl get deployment mcp-server -n mcp-server -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="APPLICATIONINSIGHTS_CONNECTION_STRING")].value}'
   ```

2. Verify OpenTelemetry exports:
   ```bash
   kubectl logs -n mcp-server -l app=mcp-server | grep "Exporting"
   ```

3. Check Application Insights ingestion:
   ```kusto
   requests
   | where timestamp > ago(5m)
   | count
   ```

### Missing Trace Context

Ensure APIM forwards trace headers:

```xml
<set-header name="traceparent" exists-action="skip">
    <value>@($"00-{context.RequestId}-{Guid.NewGuid().ToString("N").Substring(0, 16)}-01")</value>
</set-header>
```

### High Cardinality Issues

Avoid using IDs or unique values as metric dimensions:

```python
# Bad - high cardinality
meter.create_counter("requests").add(1, {"user_id": user_id})

# Good - low cardinality
meter.create_counter("requests").add(1, {"user_type": "premium"})
```

## References

- [OpenTelemetry Python SDK](https://opentelemetry.io/docs/languages/python/)
- [Azure Monitor OpenTelemetry](https://learn.microsoft.com/azure/azure-monitor/app/opentelemetry-enable?tabs=python)
- [Application Insights Overview](https://learn.microsoft.com/azure/azure-monitor/app/app-insights-overview)
- [Microsoft Sentinel](https://learn.microsoft.com/azure/sentinel/overview)
- [Kusto Query Language](https://learn.microsoft.com/azure/data-explorer/kusto/query/)
