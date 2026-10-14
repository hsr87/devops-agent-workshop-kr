"""Send a sample alert straight to the DevOps Agent webhook (no Lambda needed).

Usage:
  export WEBHOOK_URL=... WEBHOOK_SECRET=...   # from the Agent Space webhook .csv
  python3 send_test_alert.py samples/impressions-drop-during-match.json
  python3 send_test_alert.py samples/order-errors-spike.json --dry-run
"""


from __future__ import annotations
import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from lambda_function import build_payload, send


def fill_window(alert: dict) -> dict:
    """Resolve "auto" fields: the window becomes the last 30 minutes, and observed/expected
    are derived from the event-context MCP baseline so the demo verdict is deterministic."""
    now = datetime.now(timezone.utc)
    if alert.get("window_start") == "auto":
        alert["window_start"] = (now - timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    if alert.get("window_end") == "auto":
        alert["window_end"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    if "auto" in (alert.get("expected"), alert.get("observed")):
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "event-context-mcp"))
        from server import get_metric_baseline

        expected = get_metric_baseline(alert["metric"])["expected"]
        alert["expected"] = expected
        alert["observed"] = round(expected * (1 + alert["deviation_pct"] / 100), 4)
    return alert


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("sample", help="alert JSON file")
    parser.add_argument("--dry-run", action="store_true", help="print the payload without sending")
    args = parser.parse_args()

    with open(args.sample, encoding="utf-8") as f:
        alert = fill_window(json.load(f))
    payload = build_payload(alert)

    if args.dry_run:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    status, text = send(payload)
    print(f"incidentId={payload['incidentId']} status={status} response={text}")
    return 0 if status == 200 else 1


if __name__ == "__main__":
    sys.exit(main())
