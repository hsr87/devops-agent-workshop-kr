#!/usr/bin/env bash
# Run in AWS CloudShell (us-east-1) after cloning this repo. Also works in the VS Code IDE.
# Checks prerequisites, builds a Python 3.10+ venv for the extension labs, and writes
# ~/.ext-workshop.env with the values the labs need. Safe to re-run.
set -uo pipefail

REGION="${AWS_REGION:-us-east-1}"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$REPO_DIR/.venv"
ENV_FILE="$HOME/.ext-workshop.env"
ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; }
warn() { printf '  \033[33m!\033[0m %s\n' "$1"; }

echo "== AWS identity"
if ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null); then
  ok "account $ACCOUNT_ID (region $REGION)"
else
  warn "AWS credentials not found - open CloudShell from the Workshop Studio console and retry"; exit 1
fi

echo "== Workshop stack"
STACK_STATUS=$(aws cloudformation describe-stacks --region "$REGION" \
  --query "Stacks[?contains(StackName,'devops-mttr-workshop') || StackName=='cloudformation-template'].[StackName,StackStatus]" \
  --output text 2>/dev/null)
[ -n "$STACK_STATUS" ] && ok "$STACK_STATUS" || warn "workshop stack not found (self-paced account?)"

echo "== Python venv for the extension labs ($VENV)"
# CloudShell's system python3 is 3.9; the anthropic SDK needs 3.10+. When the system Python
# is too old, uv fetches a standalone Python 3.12 into $HOME, which persists across sessions.
if python3 -c 'import sys; sys.exit(sys.version_info < (3, 10))' 2>/dev/null; then
  PY_OK=1
else
  PY_OK=0
fi
if [ -x "$VENV/bin/python" ] && "$VENV/bin/python" -c 'import sys, boto3, anthropic, pydantic; sys.exit(sys.version_info < (3, 10))' 2>/dev/null; then
  ok "existing venv is ready"
else
  rm -rf "$VENV"
  if [ "$PY_OK" = 1 ]; then
    python3 -m venv "$VENV" >/dev/null 2>&1
  else
    echo "  system python is $(python3 -V 2>&1 | cut -d' ' -f2); installing Python 3.12 with uv (about 1 minute)..."
    UV="$HOME/.local/bin/uv"
    [ -x "$UV" ] || python3 -m pip install --user -q uv >/dev/null 2>&1
    # Fallback when the system Python has no pip: uv's official standalone installer.
    [ -x "$UV" ] || (curl -LsSf https://astral.sh/uv/install.sh | env UV_NO_MODIFY_PATH=1 sh) >/dev/null 2>&1
    [ -x "$UV" ] && "$UV" venv -q -p 3.12 --seed "$VENV" >/dev/null 2>&1
  fi
  if [ -x "$VENV/bin/python" ] && "$VENV/bin/python" -m pip install -q \
       -r "$REPO_DIR/extensions/rca-eval/requirements.txt" \
       -r "$REPO_DIR/extensions/triage-router/requirements.txt" >/dev/null 2>&1; then
    ok "$("$VENV/bin/python" -V): boto3, anthropic, pydantic installed"
  else
    warn "venv setup failed - triage-router and rca-eval --judge need it. Re-run this script or ask the facilitator"
  fi
fi

echo "== DevOps Agent Space"
# Looked up with boto3 from the venv, so it works even if this shell's AWS CLI predates DevOps Agent.
AGENT_SPACE_ID=$("$VENV/bin/python" - "$REGION" 2>/dev/null <<'PY'
import sys, boto3
client = boto3.client("devops-agent", region_name=sys.argv[1])
for page in client.get_paginator("list_agent_spaces").paginate():
    for space in page.get("agentSpaces", []):
        if space.get("name") == "api-error-incident-space":
            print(space["agentSpaceId"]); sys.exit()
PY
)
if [ -n "$AGENT_SPACE_ID" ]; then
  ok "api-error-incident-space = $AGENT_SPACE_ID"
else
  warn "Agent Space 'api-error-incident-space' not found - create it first, then re-run this script"
fi

# Keep webhook values that were already filled in (re-running must not wipe them).
WEBHOOK_URL_LINE=$(grep '^export WEBHOOK_URL=[^$]' "$ENV_FILE" 2>/dev/null || echo 'export WEBHOOK_URL=${WEBHOOK_URL:-}')
WEBHOOK_SECRET_LINE=$(grep '^export WEBHOOK_SECRET=[^$]' "$ENV_FILE" 2>/dev/null || echo 'export WEBHOOK_SECRET=${WEBHOOK_SECRET:-}')

(umask 077; cat > "$ENV_FILE") <<ENVEOF
export AWS_REGION=$REGION
export AWS_ACCOUNT_ID=$ACCOUNT_ID
export AGENT_SPACE_ID=$AGENT_SPACE_ID
export EXT_REPO=$REPO_DIR
export EXT_PYTHON=$VENV/bin/python
# Fill these in from the webhook .csv you download in Part 1 (Proactive investigation):
$WEBHOOK_URL_LINE
$WEBHOOK_SECRET_LINE
ENVEOF
chmod 600 "$ENV_FILE"   # holds the webhook secret
echo
echo "Wrote $ENV_FILE. Load it in every new shell tab with:  source ~/.ext-workshop.env"
