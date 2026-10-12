#!/usr/bin/env bash
# Run inside the Workshop Studio VS Code terminal after cloning this repo.
# Checks prerequisites and writes ~/.ext-workshop.env with values the extension labs need.
set -uo pipefail

REGION="${AWS_REGION:-us-east-1}"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$HOME/.ext-workshop.env"
ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; }
warn() { printf '  \033[33m!\033[0m %s\n' "$1"; }

echo "== AWS identity"
if ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null); then
  ok "account $ACCOUNT_ID (region $REGION)"
else
  warn "AWS credentials not found - open the IDE from Workshop Studio and retry"; exit 1
fi

echo "== Workshop stack"
STACK_STATUS=$(aws cloudformation describe-stacks --region "$REGION" \
  --query "Stacks[?contains(StackName,'devops-mttr-workshop') || StackName=='cloudformation-template'].[StackName,StackStatus]" \
  --output text 2>/dev/null)
[ -n "$STACK_STATUS" ] && ok "$STACK_STATUS" || warn "workshop stack not found (self-paced account?)"

echo "== DevOps Agent Space"
AGENT_SPACE_ID=$(aws devops-agent list-agent-spaces --region "$REGION" \
  --query "agentSpaces[?name=='api-error-incident-space'].agentSpaceId | [0]" --output text 2>/dev/null)
if [ -n "$AGENT_SPACE_ID" ] && [ "$AGENT_SPACE_ID" != "None" ]; then
  ok "api-error-incident-space = $AGENT_SPACE_ID"
else
  AGENT_SPACE_ID=""
  warn "Agent Space 'api-error-incident-space' not found - create it first (Getting Started > Setup your AWS environment)"
fi

echo "== Python packages for the extension labs (venv: $REPO_DIR/.venv)"
if python3 -m venv "$REPO_DIR/.venv" >/dev/null 2>&1 \
   && "$REPO_DIR/.venv/bin/pip" install -q -r "$REPO_DIR/extensions/rca-eval/requirements.txt" -r "$REPO_DIR/extensions/triage-router/requirements.txt" >/dev/null 2>&1; then
  ok "boto3, anthropic, pydantic installed - run the judge with $REPO_DIR/.venv/bin/python"
else
  warn "venv/pip failed - triage-router and rca-eval --judge need these packages"
fi

cat > "$ENV_FILE" <<ENVEOF
export AWS_REGION=$REGION
export AWS_ACCOUNT_ID=$ACCOUNT_ID
export AGENT_SPACE_ID=$AGENT_SPACE_ID
export EXT_REPO=$REPO_DIR
export EXT_PYTHON=$REPO_DIR/.venv/bin/python
# Fill these in from the webhook .csv you download in Part 1 (Proactive investigation):
export WEBHOOK_URL=\${WEBHOOK_URL:-}
export WEBHOOK_SECRET=\${WEBHOOK_SECRET:-}
ENVEOF
echo
echo "Wrote $ENV_FILE. Load it in any terminal with:  source ~/.ext-workshop.env"
