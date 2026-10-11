#!/usr/bin/env bash
# Register the deployed MCP server with AWS DevOps Agent (account level) and allow its
# read-only tools in an Agent Space. Same result as Settings > MCP servers in the console.
# Usage: AGENT_SPACE_ID=... ./register.sh
set -euo pipefail
REGION="${AWS_REGION:-us-east-1}"
: "${AGENT_SPACE_ID:?set AGENT_SPACE_ID (DevOps Agent console > Agent Space > ID)}"
cd "$(dirname "$0")"
set -a; source .mcp-endpoint.env; set +a

SERVICE_ID=$(aws devops-agent register-service --region "$REGION" --service mcpserver \
  --name event-context-mcp \
  --service-details "$(python3 - <<PY
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

TOOLS='["list_external_events","get_metric_baseline","explain_deviation","get_service_owner"]'
aws devops-agent associate-service --region "$REGION" --agent-space-id "$AGENT_SPACE_ID" \
  --service-id "$SERVICE_ID" \
  --configuration "{\"mcpserver\": {\"tools\": $TOOLS, \"toolDetails\": $(python3 -c "import json;print(json.dumps([{'name':t,'toolClassification':'READ_ONLY'} for t in json.loads('$TOOLS')]))")}}" >/dev/null
echo "Associated with Agent Space $AGENT_SPACE_ID (tools: $TOOLS)"
