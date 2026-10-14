"""Forward any alert (business metric alert, CloudWatch alarm, custom JSON) to an
AWS DevOps Agent generic webhook so an investigation starts automatically.

Only `title`, `description`, `priority` and the incident reference reach the
agent - the free-form `data` field is accepted but NOT used as investigation
context. So everything the agent needs (metric, observed vs expected, window,
hints) is rendered into `description`.

Environment variables:
  WEBHOOK_URL     DevOps Agent generic webhook URL
  WEBHOOK_SECRET  HMAC signing secret (AUTH_MODE=hmac) or API key (AUTH_MODE=bearer)
  AUTH_MODE       "hmac" (default) or "bearer"
  AWS_ACCOUNT_ID  optional, included in the description
  TARGET_REGION   optional, included in the description (default us-east-1)
"""


from __future__ import annotations
import base64
import hashlib
import hmac
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

PRIORITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "MINIMAL"}

# Appended to every description: tells the agent how to separate a real incident
# from an expected business fluctuation and what evidence to return for routing.
TRIAGE_GUIDANCE = (
    "Investigation guidance:\n"
    "1. Before concluding this is an incident, check whether the deviation is explained by "
    "external events (sports matches, promotions, holidays) or normal seasonality. If the "
    "event-context MCP tools are available, call explain_deviation and list_external_events.\n"
    "2. State a verdict: INCIDENT, EXPECTED_EVENT, or INCONCLUSIVE, with the evidence for it.\n"
    "3. If INCIDENT, identify the owning service/team (use get_service_owner if available) and "
    "list the evidence that points to that domain and the hypotheses you ruled out."
)


def _now_iso_ms() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _normalize_priority(value) -> str:
    value = str(value or "HIGH").upper()
    return value if value in PRIORITIES else "HIGH"


def build_payload(alert: dict) -> dict:
    """Convert a supported alert shape into the DevOps Agent webhook payload."""
    account = os.environ.get("AWS_ACCOUNT_ID", "")
    region = os.environ.get("TARGET_REGION", "us-east-1")
    scope = f"AWS account {account} region {region}" if account else f"region {region}"

    if alert.get("detail-type") == "CloudWatch Alarm State Change":
        detail = alert.get("detail", {})
        name = detail.get("alarmName", "unknown-alarm")
        state = detail.get("state", {})
        title = f"CloudWatch alarm {name} is {state.get('value', 'ALARM')}"
        lines = [
            f"Alarm: {name}",
            f"Reason: {state.get('reason', '')}",
            f"Scope: {scope}",
        ]
        service = name
        source = "cloudwatch"
        priority = "HIGH"
    elif alert.get("source") == "biz-metric-alert":
        metric = alert["metric"]
        service = alert.get("service", "unknown-service")
        title = (
            f"{metric} {alert.get('direction', 'deviation')} "
            f"{alert.get('deviation_pct', '?')}% on {service}"
        )
        lines = [
            f"Business metric alert from {alert.get('alert_system', 'metric alert system')}.",
            f"Metric: {metric} (service: {service}, market: {alert.get('market', 'n/a')})",
            f"Observed: {alert.get('observed')} / Expected: {alert.get('expected')} "
            f"({alert.get('deviation_pct')}% vs baseline)",
            f"Window: {alert.get('window_start')} ~ {alert.get('window_end')}",
            f"Related infrastructure: {', '.join(alert.get('related_resources', [])) or 'n/a'}",
            f"Scope: {scope}",
        ]
        if alert.get("dashboard"):
            lines.append(f"Dashboard: {alert['dashboard']}")
        source = "biz"
        priority = alert.get("severity", "HIGH")
    else:
        title = alert.get("title") or "External alert"
        service = alert.get("service", "unknown-service")
        lines = [alert.get("description", json.dumps(alert, ensure_ascii=False)), f"Scope: {scope}"]
        source = "generic"
        priority = alert.get("priority", "HIGH")

    description = "\n".join(lines) + "\n\n" + TRIAGE_GUIDANCE
    timestamp = _now_iso_ms()
    return {
        "eventType": "incident",
        # Must be unique per event: duplicate incidentId/timestamp pairs are deduplicated.
        "incidentId": f"{source}-{service}-{int(time.time() * 1000)}"[:128],
        "action": "created",
        "priority": _normalize_priority(priority),
        "title": title[:250],
        "description": description,
        "timestamp": timestamp,
        "service": service,
        "data": {"original_alert": alert},
    }


def send(payload: dict) -> tuple[int, str]:
    url = os.environ["WEBHOOK_URL"]
    secret = os.environ["WEBHOOK_SECRET"]
    mode = os.environ.get("AUTH_MODE", "hmac").lower()

    body = json.dumps(payload, ensure_ascii=False)
    timestamp = payload["timestamp"]
    headers = {"Content-Type": "application/json", "x-amzn-event-timestamp": timestamp}
    if mode == "bearer":
        headers["Authorization"] = f"Bearer {secret}"
    else:
        digest = hmac.new(secret.encode(), f"{timestamp}:{body}".encode(), hashlib.sha256).digest()
        headers["x-amzn-event-signature"] = base64.b64encode(digest).decode()

    req = urllib.request.Request(url, data=body.encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def handler(event, context):
    """Lambda entry point: direct invoke with an alert JSON, or an EventBridge alarm event."""
    payload = build_payload(event)
    status, text = send(payload)
    print(json.dumps({"incidentId": payload["incidentId"], "status": status, "response": text}))
    return {"statusCode": status, "incidentId": payload["incidentId"], "response": text}
