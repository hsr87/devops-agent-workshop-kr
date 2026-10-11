#!/usr/bin/env bash
# Deploy the event-context MCP server as Lambda + API Gateway HTTP API (public HTTPS,
# required by AWS DevOps Agent), protected by an API key header.
set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
FUNCTION_NAME="ext-event-context-mcp"
ROLE_NAME="ext-event-context-mcp-role"
API_NAME="ext-event-context-mcp"
cd "$(dirname "$0")"

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
MCP_API_KEY="${MCP_API_KEY:-$(openssl rand -hex 24)}"

if ! aws iam get-role --role-name "$ROLE_NAME" >/dev/null 2>&1; then
  aws iam create-role --role-name "$ROLE_NAME" --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{"Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"}, "Action": "sts:AssumeRole"}]
  }' >/dev/null
  aws iam attach-role-policy --role-name "$ROLE_NAME" \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
  echo "Waiting 10s for IAM propagation..."
  sleep 10
fi

rm -f /tmp/ext-event-context-mcp.zip
python3 -m zipfile -c /tmp/ext-event-context-mcp.zip server.py data
ENV="Variables={MCP_API_KEY=${MCP_API_KEY}}"

if aws lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" >/dev/null 2>&1; then
  aws lambda update-function-code --function-name "$FUNCTION_NAME" \
    --zip-file fileb:///tmp/ext-event-context-mcp.zip --region "$REGION" >/dev/null
  aws lambda wait function-updated --function-name "$FUNCTION_NAME" --region "$REGION"
  aws lambda update-function-configuration --function-name "$FUNCTION_NAME" \
    --environment "$ENV" --region "$REGION" >/dev/null
else
  aws lambda create-function --function-name "$FUNCTION_NAME" \
    --runtime python3.12 --handler server.lambda_handler \
    --role "arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}" \
    --zip-file fileb:///tmp/ext-event-context-mcp.zip --timeout 15 \
    --environment "$ENV" --region "$REGION" >/dev/null
fi
aws lambda wait function-active-v2 --function-name "$FUNCTION_NAME" --region "$REGION"
FUNCTION_ARN=$(aws lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" --query Configuration.FunctionArn --output text)

API_ID=$(aws apigatewayv2 get-apis --region "$REGION" --query "Items[?Name=='${API_NAME}'].ApiId | [0]" --output text)
if [ "$API_ID" = "None" ] || [ -z "$API_ID" ]; then
  # Quick create: HTTP API with a default route proxying to the Lambda.
  API_ID=$(aws apigatewayv2 create-api --name "$API_NAME" --protocol-type HTTP \
    --target "$FUNCTION_ARN" --region "$REGION" --query ApiId --output text)
  aws lambda add-permission --function-name "$FUNCTION_NAME" --statement-id apigw-invoke \
    --action lambda:InvokeFunction --principal apigateway.amazonaws.com \
    --source-arn "arn:aws:execute-api:${REGION}:${ACCOUNT_ID}:${API_ID}/*" --region "$REGION" >/dev/null
fi
ENDPOINT=$(aws apigatewayv2 get-api --api-id "$API_ID" --region "$REGION" --query ApiEndpoint --output text)

cat > .mcp-endpoint.env <<ENVEOF
MCP_URL=${ENDPOINT}/mcp
MCP_API_KEY=${MCP_API_KEY}
ENVEOF
echo "MCP endpoint : ${ENDPOINT}/mcp"
echo "API key      : saved to $(pwd)/.mcp-endpoint.env (header: x-api-key)"
echo "Smoke test   : set -a; source .mcp-endpoint.env; set +a; ./test_mcp.sh"
