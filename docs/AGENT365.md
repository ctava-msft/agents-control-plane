# Agent365: Human-in-the-Loop Control Plane

Agent365 provides a human-in-the-loop approval workflow for AI agents, enabling human oversight and control over sensitive or high-impact operations.

## Overview

Agent365 allows AI agents to request human approval before executing certain actions. This is critical for:

- **Sensitive Operations**: Data deletion, financial transactions, system configuration changes
- **Compliance**: Regulatory requirements for human review
- **Quality Control**: Human validation of AI decisions
- **Safety**: Preventing unintended consequences

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  AI Agent                                            │
│  └── Requests approval for sensitive action         │
└────────────────┬────────────────────────────────────┘
                 │ MCP Tool: request_approval
                 ↓
┌─────────────────────────────────────────────────────┐
│  MCP Server                                          │
│  ├── Creates approval request                       │
│  ├── Generates unique approval ID                   │
│  └── Queues request in Azure Storage Queue          │
└────────────────┬────────────────────────────────────┘
                 │ Approval Request Message
                 ↓
┌─────────────────────────────────────────────────────┐
│  Azure Storage Queue (agent365-approvals)           │
│  └── Approval requests awaiting human review        │
└────────────────┬────────────────────────────────────┘
                 │ Human reviews via...
                 ↓
┌─────────────────────────────────────────────────────┐
│  Human Oversight Interface                          │
│  ├── Web Dashboard (Azure Static Web Apps)          │
│  ├── Teams Bot (Power Automate)                     │
│  ├── Email Notifications (Logic Apps)               │
│  └── Mobile App (Power Apps)                        │
└────────────────┬────────────────────────────────────┘
                 │ Approval Decision
                 ↓
┌─────────────────────────────────────────────────────┐
│  Approval Database (Azure Table Storage)            │
│  └── Approval history with decisions                │
└────────────────┬────────────────────────────────────┘
                 │ Agent polls for decision
                 ↓
┌─────────────────────────────────────────────────────┐
│  AI Agent                                            │
│  └── Proceeds or aborts based on approval           │
└─────────────────────────────────────────────────────┘
```

## MCP Tools

### request_approval

Request human approval for a sensitive action.

**Input Schema:**
```json
{
  "action": "Delete all customer data older than 7 years",
  "context": "GDPR compliance cleanup. Affects 15,000 records.",
  "requester": "data-cleanup-agent-v2"
}
```

**Response:**
```json
{
  "content": [{
    "type": "text",
    "text": "Approval request submitted. ID: 550e8400-e29b-41d4-a716-446655440000\nStatus: pending\nAction: Delete all customer data older than 7 years"
  }],
  "isError": false
}
```

**Approval Request Structure:**
```json
{
  "approval_id": "550e8400-e29b-41d4-a716-446655440000",
  "action": "Delete all customer data older than 7 years",
  "context": "GDPR compliance cleanup. Affects 15,000 records.",
  "requester": "data-cleanup-agent-v2",
  "status": "pending",
  "created_at": "2024-01-14T00:15:44.157Z"
}
```

### check_approval_status

Check the status of a pending approval request.

**Input Schema:**
```json
{
  "approval_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response:**
```json
{
  "content": [{
    "type": "text",
    "text": "Approval ID: 550e8400-e29b-41d4-a716-446655440000\nStatus: pending\n\nNote: This is a demo implementation. In production, integrate with approval management system."
  }],
  "isError": false
}
```

## Example Workflow

### 1. Agent Requests Approval

```python
import requests
import json

# Agent identifies a sensitive operation
if is_sensitive_operation(action):
    # Request approval via MCP
    response = requests.post(
        "https://your-apim.azure-api.net/mcp/message",
        headers={"Authorization": f"Bearer {mcp_token}"},
        json={
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "request_approval",
                "arguments": {
                    "action": "Delete customer PII",
                    "context": "GDPR right-to-erasure request",
                    "requester": "compliance-agent"
                }
            },
            "id": 1
        }
    )
    
    approval_id = extract_approval_id(response.json())
    print(f"Waiting for approval: {approval_id}")
```

### 2. Human Reviews Request

Approval requests appear in the approval queue. Humans can review via:

**Azure Portal:**
```bash
# View pending approvals
az storage message peek --queue-name agent365-approvals \
  --account-name $STORAGE_ACCOUNT_NAME \
  --num-messages 10
```

**Power Automate Flow:**
```yaml
Trigger: When a message is added to queue
Actions:
  1. Parse JSON (approval request)
  2. Send Teams adaptive card
  3. Wait for approval response
  4. Update approval status
```

### 3. Agent Polls for Decision

```python
import time

# Poll for approval status
max_wait = 300  # 5 minutes
interval = 10   # 10 seconds
elapsed = 0

while elapsed < max_wait:
    response = requests.post(
        "https://your-apim.azure-api.net/mcp/message",
        headers={"Authorization": f"Bearer {mcp_token}"},
        json={
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "check_approval_status",
                "arguments": {
                    "approval_id": approval_id
                }
            },
            "id": 2
        }
    )
    
    status = extract_status(response.json())
    
    if status == "approved":
        print("Approval granted - proceeding")
        execute_action()
        break
    elif status == "rejected":
        print("Approval denied - aborting")
        break
    else:
        print(f"Still pending... {elapsed}s elapsed")
        time.sleep(interval)
        elapsed += interval
```

## Human Oversight Interface Options

### Option 1: Power Automate + Teams

**Pros:**
- No code required
- Native Teams integration
- Fast to deploy

**Implementation:**
1. Create Power Automate flow
2. Trigger on Storage Queue message
3. Send adaptive card to Teams channel
4. Capture approve/reject response
5. Update approval status

**Teams Adaptive Card:**
```json
{
  "type": "AdaptiveCard",
  "body": [
    {
      "type": "TextBlock",
      "text": "Approval Required",
      "weight": "bolder",
      "size": "large"
    },
    {
      "type": "TextBlock",
      "text": "Action: ${action}",
      "wrap": true
    },
    {
      "type": "TextBlock",
      "text": "Context: ${context}",
      "wrap": true
    },
    {
      "type": "TextBlock",
      "text": "Requester: ${requester}",
      "wrap": true
    }
  ],
  "actions": [
    {
      "type": "Action.Submit",
      "title": "Approve",
      "data": {"approval_id": "${approval_id}", "decision": "approved"}
    },
    {
      "type": "Action.Submit",
      "title": "Reject",
      "data": {"approval_id": "${approval_id}", "decision": "rejected"}
    }
  ]
}
```

### Option 2: Azure Static Web Apps

**Pros:**
- Custom UI/UX
- Mobile responsive
- Full control

**Implementation:**
1. Deploy React/Vue.js SPA to Azure Static Web Apps
2. Use Azure Functions backend for API
3. Query approval queue
4. Display in web dashboard
5. Submit approval decisions

**Sample React Component:**
```jsx
function ApprovalDashboard() {
  const [approvals, setApprovals] = useState([]);
  
  useEffect(() => {
    // Fetch pending approvals
    fetch('/api/approvals/pending')
      .then(res => res.json())
      .then(data => setApprovals(data));
  }, []);
  
  const handleApproval = (approvalId, decision) => {
    fetch('/api/approvals/decide', {
      method: 'POST',
      body: JSON.stringify({ approvalId, decision })
    });
  };
  
  return (
    <div>
      <h1>Pending Approvals</h1>
      {approvals.map(approval => (
        <ApprovalCard
          key={approval.approval_id}
          approval={approval}
          onApprove={() => handleApproval(approval.approval_id, 'approved')}
          onReject={() => handleApproval(approval.approval_id, 'rejected')}
        />
      ))}
    </div>
  );
}
```

### Option 3: Power Apps Mobile

**Pros:**
- Mobile-first
- Offline capable
- Integration with Office 365

**Implementation:**
1. Create Power Apps canvas app
2. Connect to Azure Storage Queue
3. Build approval interface
4. Deploy to mobile devices

## Identity Federation for Non-Azure Agents

External agents (GitHub Actions, AWS Lambda, etc.) can participate in Agent365 using federated credentials.

### GitHub Actions Integration

```yaml
name: Automated Deployment with Agent365
on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Target environment'
        required: true

permissions:
  id-token: write

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Azure Login (OIDC)
        uses: azure/login@v1
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
      
      - name: Request Approval
        id: approval
        run: |
          # Get MCP token
          TOKEN=$(az account get-access-token --resource api://mcp-server --query accessToken -o tsv)
          
          # Request approval
          RESPONSE=$(curl -X POST https://your-apim.azure-api.net/mcp/message \
            -H "Authorization: Bearer $TOKEN" \
            -H "Content-Type: application/json" \
            -d '{
              "method": "tools/call",
              "params": {
                "name": "request_approval",
                "arguments": {
                  "action": "Deploy to production",
                  "context": "Version 2.1.0 with security fixes",
                  "requester": "github-actions"
                }
              }
            }')
          
          APPROVAL_ID=$(echo $RESPONSE | jq -r '.result.approval_id')
          echo "approval_id=$APPROVAL_ID" >> $GITHUB_OUTPUT
      
      - name: Wait for Approval
        run: |
          # Poll for approval (simplified)
          for i in {1..30}; do
            STATUS=$(curl -X POST https://your-apim.azure-api.net/mcp/message \
              -H "Authorization: Bearer $TOKEN" \
              -d '{"method":"tools/call","params":{"name":"check_approval_status","arguments":{"approval_id":"${{ steps.approval.outputs.approval_id }}"}}}' \
              | jq -r '.result.status')
            
            if [ "$STATUS" == "approved" ]; then
              echo "Approval granted!"
              break
            elif [ "$STATUS" == "rejected" ]; then
              echo "Approval rejected!"
              exit 1
            fi
            
            sleep 10
          done
      
      - name: Deploy Application
        run: |
          echo "Deploying to production..."
          # Actual deployment steps
```

### AWS Lambda Integration

```python
import boto3
import requests
import json
from azure.identity import DefaultAzureCredential

def lambda_handler(event, context):
    # Use federated credential to get Azure token
    credential = DefaultAzureCredential()
    token = credential.get_token("api://mcp-server")
    
    # Request approval
    response = requests.post(
        "https://your-apim.azure-api.net/mcp/message",
        headers={"Authorization": f"Bearer {token.token}"},
        json={
            "method": "tools/call",
            "params": {
                "name": "request_approval",
                "arguments": {
                    "action": event['action'],
                    "context": event['context'],
                    "requester": "aws-lambda"
                }
            }
        }
    )
    
    approval_id = response.json()['result']['approval_id']
    
    # Store approval ID in DynamoDB for async processing
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('approvals')
    table.put_item(Item={
        'approval_id': approval_id,
        'status': 'pending',
        'created_at': datetime.utcnow().isoformat()
    })
    
    return {
        'statusCode': 202,
        'body': json.dumps({'approval_id': approval_id})
    }
```

## Approval Workflow Patterns

### Pattern 1: Synchronous Approval

Agent waits for human decision before proceeding:

```python
approval_id = request_approval(action)
wait_for_approval(approval_id, timeout=300)
if is_approved(approval_id):
    execute_action()
else:
    log_rejection()
```

### Pattern 2: Asynchronous Approval

Agent submits request and continues other work:

```python
approval_id = request_approval(action)
queue_action_for_later(action, approval_id)
# Continue with other tasks
```

Later, a background job checks approvals:
```python
pending_actions = get_pending_actions()
for action in pending_actions:
    if is_approved(action.approval_id):
        execute_action(action)
        mark_complete(action)
```

### Pattern 3: Auto-Approval with Audit

Low-risk actions auto-approve after delay:

```python
approval_id = request_approval(action, risk="low")
time.sleep(300)  # 5 minute review window
if not is_explicitly_rejected(approval_id):
    auto_approve(approval_id)
    execute_action()
```

## Security Considerations

1. **Authentication**: Only authenticated agents can request approvals
2. **Authorization**: Validate requester has permission to perform action
3. **Audit Trail**: Log all approval requests and decisions
4. **Timeout**: Implement approval timeouts to avoid indefinite waits
5. **Escalation**: Escalate urgent approvals to on-call personnel

## Monitoring and Alerts

### Key Metrics

- **Pending Approval Count**: Number of approvals waiting for review
- **Average Resolution Time**: Time from request to decision
- **Approval Rate**: Percentage of approved vs rejected
- **Timeout Rate**: Percentage of approvals that timed out

### Sample Alerts

**Long Pending Approval:**
```kusto
let threshold = 30m;
StorageQueueLogs
| where QueueName == "agent365-approvals"
| where OperationName == "PutMessage"
| extend age = now() - TimeGenerated
| where age > threshold
| summarize count() by bin(TimeGenerated, 5m)
```

**High Rejection Rate:**
```kusto
customEvents
| where name == "approval_decision"
| summarize 
    total = count(),
    rejected = countif(customDimensions.decision == "rejected")
| extend rejection_rate = rejected * 100.0 / total
| where rejection_rate > 50
```

## Best Practices

1. **Clear Context**: Provide detailed information about the action
2. **Risk Classification**: Tag requests with risk level (low/medium/high)
3. **SLA Targets**: Set and monitor approval SLA targets
4. **Escalation Path**: Define escalation for urgent or critical approvals
5. **Regular Reviews**: Periodically review approval patterns and adjust policies

## Future Enhancements

- **Machine Learning**: Auto-approve based on historical patterns
- **Multi-Stage Approval**: Require multiple approvers for high-risk actions
- **Conditional Approval**: Approve with modifications/constraints
- **Role-Based Routing**: Route approvals based on action type
- **Integration with ServiceNow**: Enterprise change management integration

## References

- [Azure Storage Queues](https://learn.microsoft.com/azure/storage/queues/)
- [Power Automate](https://learn.microsoft.com/power-automate/)
- [Teams Adaptive Cards](https://learn.microsoft.com/microsoftteams/platform/task-modules-and-cards/cards/cards-reference#adaptive-card)
- [Azure Static Web Apps](https://learn.microsoft.com/azure/static-web-apps/)
- [Human-in-the-Loop AI](https://www.microsoft.com/en-us/ai/ai-lab-human-ai-collaboration)
