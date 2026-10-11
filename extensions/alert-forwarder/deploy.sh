#!/usr/bin/env bash
# (Optional) Deploy the alert forwarder as a Lambda so an existing alerting system
# (or EventBridge) can call it. Requires WEBHOOK_URL and WEBHOOK_SECRET in the environment.
set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
FUNCTION_NAME="ext-alert-forwarder"
ROLE_NAME="ext-alert-forwarder-role"
AUTH_MODE="${AUTH_MODE:-hmac}"
: "${WEBHOOK_URL:?set WEBHOOK_URL}" "${WEBHOOK_SECRET:?set WEBHOOK_SECRET}"

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
cd "$(dirname "$0")"

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

rm -f /tmp/ext-alert-forwarder.zip
python3 -m zipfile -c /tmp/ext-alert-forwarder.zip lambda_function.py
ENV="Variables={WEBHOOK_URL=${WEBHOOK_URL},WEBHOOK_SECRET=${WEBHOOK_SECRET},AUTH_MODE=${AUTH_MODE},AWS_ACCOUNT_ID=${ACCOUNT_ID},TARGET_REGION=${REGION}}"

if aws lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" >/dev/null 2>&1; then
  aws lambda update-function-code --function-name "$FUNCTION_NAME" \
    --zip-file fileb:///tmp/ext-alert-forwarder.zip --region "$REGION" >/dev/null
  aws lambda wait function-updated --function-name "$FUNCTION_NAME" --region "$REGION"
  aws lambda update-function-configuration --function-name "$FUNCTION_NAME" \
    --environment "$ENV" --region "$REGION" >/dev/null
else
  aws lambda create-function --function-name "$FUNCTION_NAME" \
    --runtime python3.12 --handler lambda_function.handler \
    --role "arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}" \
    --zip-file fileb:///tmp/ext-alert-forwarder.zip --timeout 30 \
    --environment "$ENV" --region "$REGION" >/dev/null
fi
aws lambda wait function-active-v2 --function-name "$FUNCTION_NAME" --region "$REGION"

echo "Deployed ${FUNCTION_NAME}. Test it with:"
echo "  python3 render_sample.py samples/impressions-drop-during-match.json > /tmp/alert.json"
echo "  aws lambda invoke --function-name ${FUNCTION_NAME} --payload fileb:///tmp/alert.json /tmp/out.json && cat /tmp/out.json"
