"""Event-context MCP server for AWS DevOps Agent (Streamable HTTP, stateless, no dependencies).

Gives the agent the business context it cannot see in telemetry:
  - list_external_events : sports matches / promotions / holidays overlapping a time window
  - get_metric_baseline  : expected value band for a business metric at a given time
  - explain_deviation    : is an observed deviation explained by baseline + known events?
  - get_service_owner    : owning team, on-call channel and domain boundaries (for routing)

Runs as a Lambda behind an API Gateway HTTP API (see deploy.sh), or locally:
  MCP_API_KEY=dev python3 server.py --port 8080
All tools are read-only.
"""

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

SERVER_NAME = "event-context-mcp"
SERVER_VERSION = "1.0.0"
SUPPORTED_PROTOCOL_VERSIONS = ["2025-06-18", "2025-03-26", "2024-11-05"]
DATA_DIR = Path(__file__).parent / "data"

# ---------------------------------------------------------------------------
# Data access (mock data in data/*.json - replace with real calendars/baselines)
# ---------------------------------------------------------------------------


def _load(name: str):
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def _parse_time(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    value = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _materialize_events(now: datetime) -> list[dict]:
    """Resolve events with relative offsets so the demo always has a 'live' event."""
    events = []
    for event in _load("events.json"):
        event = dict(event)
        if "relative_start_minutes" in event:
            start = now + timedelta(minutes=event.pop("relative_start_minutes"))
            end = start + timedelta(minutes=event.pop("duration_minutes"))
            event["start"], event["end"] = _iso(start), _iso(end)
        events.append(event)
    return events


def list_external_events(start_time: str | None = None, end_time: str | None = None,
                         market: str = "KR") -> dict:
    now = datetime.now(timezone.utc)
    start = _parse_time(start_time) if start_time else now - timedelta(hours=6)
    end = _parse_time(end_time) if end_time else now + timedelta(hours=6)
    matched = [
        e for e in _materialize_events(now)
        if e.get("market", market) == market
        and _parse_time(e["start"]) < end and _parse_time(e["end"]) > start
    ]
    return {"window": {"start": _iso(start), "end": _iso(end)}, "market": market, "events": matched}


def get_metric_baseline(metric: str, timestamp: str | None = None) -> dict:
    baselines = _load("baselines.json")
    if metric not in baselines:
        return {"error": f"unknown metric '{metric}'", "known_metrics": sorted(baselines)}
    spec = baselines[metric]
    at = _parse_time(timestamp)
    local = at + timedelta(hours=spec.get("utc_offset_hours", 9))
    profile = spec["weekend_hourly"] if local.weekday() >= 5 else spec["weekday_hourly"]
    expected = profile[local.hour]
    tolerance = spec["tolerance_pct"] / 100
    return {
        "metric": metric,
        "unit": spec["unit"],
        "timestamp": _iso(at),
        "expected": expected,
        "normal_band": [round(expected * (1 - tolerance), 4), round(expected * (1 + tolerance), 4)],
        "tolerance_pct": spec["tolerance_pct"],
        "basis": "hour-of-week seasonal profile (local time)",
    }


def explain_deviation(metric: str, observed: float, timestamp: str | None = None,
                      market: str = "KR") -> dict:
    baseline = get_metric_baseline(metric, timestamp)
    if "error" in baseline:
        return baseline
    at = _parse_time(timestamp)
    events = list_external_events(_iso(at), _iso(at + timedelta(seconds=1)), market)["events"]
    impacts = [
        {"event": e["name"], "expected_impact_pct": e["expected_impact_pct"][metric]}
        for e in events if metric in e.get("expected_impact_pct", {})
    ]
    adjustment = sum(i["expected_impact_pct"] for i in impacts) / 100
    expected = baseline["expected"]
    adjusted = expected * (1 + adjustment)
    tolerance = baseline["tolerance_pct"] / 100
    deviation_pct = round((observed - expected) / expected * 100, 1)
    residual_pct = round((observed - adjusted) / adjusted * 100, 1)

    if abs(deviation_pct) <= baseline["tolerance_pct"]:
        verdict = "WITHIN_NORMAL_RANGE"
        reason = "Observed value is inside the seasonal normal band."
    elif impacts and abs(residual_pct) <= baseline["tolerance_pct"]:
        verdict = "EXPLAINED_BY_EXTERNAL_EVENT"
        reason = "Deviation matches the expected impact of concurrent external events."
    else:
        verdict = "UNEXPLAINED_ANOMALY"
        reason = ("Deviation is larger than seasonality and known events explain; "
                  "treat as a potential incident and investigate infrastructure/application causes.")
    return {
        "metric": metric,
        "timestamp": _iso(at),
        "observed": observed,
        "seasonal_expected": expected,
        "event_adjusted_expected": round(adjusted, 4),
        "deviation_vs_seasonal_pct": deviation_pct,
        "residual_after_events_pct": residual_pct,
        "tolerance_pct": baseline["tolerance_pct"],
        "concurrent_events": impacts,
        "verdict": verdict,
        "reason": reason,
        "confidence_note": f"Tolerance {baseline['tolerance_pct']}% vs adjusted expectation {round(adjusted * (1 - tolerance), 2)}~{round(adjusted * (1 + tolerance), 2)}",
    }


def get_service_owner(service: str) -> dict:
    owners = _load("ownership.json")
    if service in owners:
        return {"service": service, **owners[service]}
    for name, info in owners.items():
        if service in info.get("aliases", []):
            return {"service": name, **info}
    return {"error": f"unknown service '{service}'", "known_services": sorted(owners)}


TOOLS = {
    "list_external_events": {
        "fn": list_external_events,
        "description": (
            "List external business events (sports matches, promotions, holidays, campaigns) that "
            "overlap a time window, with their expected impact on business metrics. Use this before "
            "declaring an incident when traffic or business metrics drop or spike."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "start_time": {"type": "string", "description": "ISO 8601 start (default: now-6h)"},
                "end_time": {"type": "string", "description": "ISO 8601 end (default: now+6h)"},
                "market": {"type": "string", "description": "Market code, default KR"},
            },
        },
    },
    "get_metric_baseline": {
        "fn": get_metric_baseline,
        "description": "Return the seasonal expected value and normal band for a business metric at a given time.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "metric": {"type": "string", "description": "e.g. ad_impressions, ad_clicks, order_success_rate"},
                "timestamp": {"type": "string", "description": "ISO 8601 time (default: now)"},
            },
            "required": ["metric"],
        },
    },
    "explain_deviation": {
        "fn": explain_deviation,
        "description": (
            "Decide whether an observed business metric value is WITHIN_NORMAL_RANGE, "
            "EXPLAINED_BY_EXTERNAL_EVENT, or an UNEXPLAINED_ANOMALY, using seasonality plus concurrent "
            "external events. Call this first when an alert is about a business metric."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "metric": {"type": "string"},
                "observed": {"type": "number"},
                "timestamp": {"type": "string", "description": "ISO 8601 time (default: now)"},
                "market": {"type": "string", "description": "Market code, default KR"},
            },
            "required": ["metric", "observed"],
        },
    },
    "get_service_owner": {
        "fn": get_service_owner,
        "description": (
            "Return the owning team, on-call channel, upstream/downstream dependencies and domain "
            "boundary for a service. Use it to route a confirmed incident to the right team."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"service": {"type": "string", "description": "Service name or alias"}},
            "required": ["service"],
        },
    },
}

# ---------------------------------------------------------------------------
# MCP (JSON-RPC 2.0 over Streamable HTTP, stateless JSON responses)
# ---------------------------------------------------------------------------


def _result(req_id, result):
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _error(req_id, code, message):
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def handle_rpc(message: dict) -> dict | None:
    """Handle one JSON-RPC message. Returns None for notifications."""
    method = message.get("method")
    req_id = message.get("id")
    params = message.get("params") or {}
    if req_id is None:  # notification (e.g. notifications/initialized)
        return None

    if method == "initialize":
        requested = params.get("protocolVersion")
        version = requested if requested in SUPPORTED_PROTOCOL_VERSIONS else SUPPORTED_PROTOCOL_VERSIONS[0]
        return _result(req_id, {
            "protocolVersion": version,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            "instructions": (
                "Business context for incident triage. For business-metric alerts call "
                "explain_deviation first; use get_service_owner to route confirmed incidents."
            ),
        })
    if method == "ping":
        return _result(req_id, {})
    if method == "tools/list":
        return _result(req_id, {"tools": [
            {"name": name, "description": t["description"], "inputSchema": t["inputSchema"],
             "annotations": {"readOnlyHint": True, "openWorldHint": False}}
            for name, t in TOOLS.items()
        ]})
    if method == "tools/call":
        name = params.get("name")
        if name not in TOOLS:
            return _error(req_id, -32602, f"Unknown tool: {name}")
        try:
            output = TOOLS[name]["fn"](**(params.get("arguments") or {}))
        except TypeError as e:
            return _result(req_id, {"content": [{"type": "text", "text": f"Invalid arguments: {e}"}], "isError": True})
        is_error = "error" in output
        return _result(req_id, {
            "content": [{"type": "text", "text": json.dumps(output, ensure_ascii=False)}],
            "structuredContent": output,
            "isError": is_error,
        })
    return _error(req_id, -32601, f"Method not found: {method}")


def _authorized(headers: dict) -> bool:
    expected = os.environ.get("MCP_API_KEY")
    if not expected:
        return False
    headers = {k.lower(): v for k, v in headers.items()}
    if headers.get("x-api-key") == expected:
        return True
    return headers.get("authorization", "") == f"Bearer {expected}"


def handle_http(method: str, headers: dict, body: str | None) -> tuple[int, dict, str]:
    """Transport-independent HTTP handling. Returns (status, headers, body)."""
    json_headers = {"Content-Type": "application/json"}
    if method != "POST":
        # Stateless server: no server-initiated SSE stream, no sessions to delete.
        return 405, {"Allow": "POST"}, ""
    if not _authorized(headers):
        return 401, json_headers, json.dumps({"error": "unauthorized"})
    try:
        message = json.loads(body or "")
    except json.JSONDecodeError:
        return 400, json_headers, json.dumps(_error(None, -32700, "Parse error"))

    if isinstance(message, list):
        responses = [r for r in (handle_rpc(m) for m in message) if r is not None]
        if not responses:
            return 202, {}, ""
        return 200, json_headers, json.dumps(responses, ensure_ascii=False)
    response = handle_rpc(message)
    if response is None:
        return 202, {}, ""
    return 200, json_headers, json.dumps(response, ensure_ascii=False)


def lambda_handler(event, context):
    """API Gateway HTTP API (payload format 2.0) entry point."""
    body = event.get("body")
    if body and event.get("isBase64Encoded"):
        import base64
        body = base64.b64decode(body).decode()
    method = event.get("requestContext", {}).get("http", {}).get("method", "POST")
    status, headers, out = handle_http(method, event.get("headers") or {}, body)
    return {"statusCode": status, "headers": headers, "body": out}


if __name__ == "__main__":
    import argparse
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    class Handler(BaseHTTPRequestHandler):
        def _respond(self, method):
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length).decode() if length else None
            status, headers, out = handle_http(method, dict(self.headers), body)
            self.send_response(status)
            for k, v in headers.items():
                self.send_header(k, v)
            self.end_headers()
            if out:
                self.wfile.write(out.encode())

        def do_POST(self):
            self._respond("POST")

        def do_GET(self):
            self._respond("GET")

    print(f"{SERVER_NAME} listening on http://localhost:{args.port}/mcp")
    ThreadingHTTPServer(("0.0.0.0", args.port), Handler).serve_forever()
