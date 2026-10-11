#!/usr/bin/env bash
# Remove the AWS resources created by the extension labs (ext-* Lambdas, roles, HTTP API).
# Does NOT touch the original workshop stack or the Agent Space.
# Optional: MCP_SERVICE_ID=... to deregister the MCP server from DevOps Agent.
set -uo pipefail
REGION="${AWS_REGION:-us-east-1}"

for fn in ext-alert-forwarder ext-event-context-mcp; do
  aws lambda delete-function --function-name "$fn" --region "$REGION" 2>/dev/null && echo "deleted lambda $fn"
done

API_ID=$(aws apigatewayv2 get-apis --region "$REGION" --query "Items[?Name=='ext-event-context-mcp'].ApiId | [0]" --output text)
[ "$API_ID" != "None" ] && [ -n "$API_ID" ] && aws apigatewayv2 delete-api --api-id "$API_ID" --region "$REGION" && echo "deleted http api $API_ID"

for role in ext-alert-forwarder-role ext-event-context-mcp-role; do
  if aws iam get-role --role-name "$role" >/dev/null 2>&1; then
    aws iam detach-role-policy --role-name "$role" \
      --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
    aws iam delete-role --role-name "$role" && echo "deleted role $role"
  fi
done

for lg in /aws/lambda/ext-alert-forwarder /aws/lambda/ext-event-context-mcp; do
  aws logs delete-log-group --log-group-name "$lg" --region "$REGION" 2>/dev/null && echo "deleted log group $lg"
done

if [ -n "${MCP_SERVICE_ID:-}" ]; then
  aws devops-agent deregister-service --service-id "$MCP_SERVICE_ID" --region "$REGION" && echo "deregistered MCP $MCP_SERVICE_ID"
fi
rm -f "$(dirname "$0")/../extensions/event-context-mcp/.mcp-endpoint.env"
echo "done"
