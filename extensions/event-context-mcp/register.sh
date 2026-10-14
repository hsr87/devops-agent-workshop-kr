#!/usr/bin/env bash
# Register the deployed MCP server with AWS DevOps Agent (account level) and allow its
# read-only tools in an Agent Space. Same result as Settings > MCP servers in the console.
# Usage: AGENT_SPACE_ID=... ./register.sh
set -euo pipefail
REGION="${AWS_REGION:-us-east-1}"
: "${AGENT_SPACE_ID:?set AGENT_SPACE_ID (DevOps Agent console > Agent Space > ID)}"
cd "$(dirname "$0")"
set -a; source .mcp-endpoint.env; set +a

# Re-running is safe: reuse the MCP server if it is already registered in this account.
SERVICE_ID=$(aws devops-agent list-services --region "$REGION" \
  --query "services[?serviceType=='mcpserver' && name=='event-context-mcp'].serviceId | [0]" --output text)
if [ -z "$SERVICE_ID" ] || [ "$SERVICE_ID" = "None" ]; then
  SERVICE_ID=$(aws devops-agent register-service --region "$REGION" --service mcpserver \
    --name event-context-mcp \
    --service-details "$(python3 - <<'PY'
import json, os
print(json.dumps({"mcpserver": {
  "name": "event-context-mcp",
  "endpoint": os.environ["MCP_URL"],
  "description": "Business context for triage: external events, metric baselines, service ownership",
  "authorizationConfig": {"apiKey": {"apiKeyName": "event-context-key",
                                      "apiKeyValue": os.environ["MCP_API_KEY"],
                                      "apiKeyHeader": "x-api-key"}}}}))
PY
)" --query serviceId --output text)
  echo "Registered MCP server: $SERVICE_ID"
else
  echo "MCP server already registered: $SERVICE_ID"
fi

# Allow the four read-only tools in the Agent Space.
CONFIG=$(python3 -c '
import json
tools = ["list_external_events", "get_metric_baseline", "explain_deviation", "get_service_owner"]
print(json.dumps({"mcpserver": {"tools": tools,
                                "toolDetails": [{"name": t, "toolClassification": "READ_ONLY"} for t in tools]}}))')
aws devops-agent associate-service --region "$REGION" --agent-space-id "$AGENT_SPACE_ID" \
  --service-id "$SERVICE_ID" --configuration "$CONFIG" >/dev/null
echo "Associated with Agent Space $AGENT_SPACE_ID (4 read-only tools)"
echo "Deregister later with: aws devops-agent deregister-service --service-id $SERVICE_ID"
