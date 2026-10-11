#!/usr/bin/env bash
# Smoke-test an event-context MCP endpoint over Streamable HTTP.
# Usage: MCP_URL=http://localhost:8080/mcp MCP_API_KEY=dev ./test_mcp.sh
set -euo pipefail
: "${MCP_URL:?set MCP_URL}" "${MCP_API_KEY:?set MCP_API_KEY}"
cd "$(dirname "$0")"
# Observed values 26% / 62% below the current seasonal baseline (computed from the same mock data).
read -r OBS_OK OBS_BAD < <(python3 -c "from server import get_metric_baseline as g; e=g('ad_impressions')['expected']; print(round(e*0.74,2), round(e*0.38,2))")

call() {
  curl -sS -X POST "$MCP_URL" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" \
    -H "x-api-key: $MCP_API_KEY" \
    -d "$1"
  echo
}

echo "== initialize";  call '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"smoke","version":"0"}}}'
echo "== initialized (expect 202)"; curl -sS -o /dev/null -w "%{http_code}\n" -X POST "$MCP_URL" -H "Content-Type: application/json" -H "x-api-key: $MCP_API_KEY" -d '{"jsonrpc":"2.0","method":"notifications/initialized"}'
echo "== tools/list";  call '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' | python3 -c "import json,sys;print([t['name'] for t in json.load(sys.stdin)['result']['tools']])"
echo "== explain_deviation (-26%, live match)"
call '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"explain_deviation","arguments":{"metric":"ad_impressions","observed":'"$OBS_OK"'}}}' | python3 -c "import json,sys;r=json.load(sys.stdin)['result']['structuredContent'];print(r['verdict'],r['deviation_vs_seasonal_pct'],r['residual_after_events_pct'])"
echo "== explain_deviation (-62%, live match)"
call '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"explain_deviation","arguments":{"metric":"ad_impressions","observed":'"$OBS_BAD"'}}}' | python3 -c "import json,sys;r=json.load(sys.stdin)['result']['structuredContent'];print(r['verdict'],r['deviation_vs_seasonal_pct'],r['residual_after_events_pct'])"
echo "== get_service_owner"
call '{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"get_service_owner","arguments":{"service":"order-processing"}}}' | python3 -c "import json,sys;r=json.load(sys.stdin)['result']['structuredContent'];print(r['service'],r['team'],r['oncall_channel'])"
echo "== unauthorized (expect 401)"; curl -sS -o /dev/null -w "%{http_code}\n" -X POST "$MCP_URL" -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","id":9,"method":"tools/list"}'
