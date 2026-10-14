"""Main agent (orchestrator) that keeps triage and routing deterministic and delegates
only the RCA to AWS DevOps Agent.

  alert ──▶ [triage] ──EXPECTED_EVENT──▶ close (no investigation, no cost)
                │
             INCIDENT
                ▼
          [investigate]  DevOps Agent API (create_backlog_task → poll → journal)
                ▼
            [route]      service catalog → candidate owner team
                ▼
         [domain_verify] that team's domain agent ACCEPTs or REJECTs with evidence
                ▼
           results.jsonl  same format rca-eval/evaluate.py reads

Every node appends {node, input, output, ms} to the trace, so "why did it go to this
team" can be audited and measured per step.

Usage:
  python3 router.py start ../alert-forwarder/samples/*.json   # triage now, start RCAs
  python3 router.py status                                    # watch DevOps Agent tasks
  python3 router.py finish [--wait]                           # route + verify, write results
  python3 router.py run <sample.json>                         # all of the above for one alert
"""


from __future__ import annotations
import argparse
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "alert-forwarder"))
sys.path.insert(0, str(HERE.parent / "event-context-mcp"))

from lambda_function import build_payload  # noqa: E402  (same description as the webhook path)
from send_test_alert import fill_window  # noqa: E402

import devops_agent_tool  # noqa: E402

RUNS = Path(os.environ.get("ROUTER_RUNS", HERE / "runs"))
DONE = {"COMPLETED", "FAILED", "TIMED_OUT", "CANCELED", "SKIPPED", "WAIT_TIMEOUT"}


# ---------- context lookups: remote MCP if MCP_URL is set, otherwise the same code locally ----------

def mcp_call(tool: str, arguments: dict) -> dict:
    url = os.environ.get("MCP_URL")
    if not url:
        import server
        return getattr(server, tool)(**arguments)
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": tool, "arguments": arguments}}
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST", headers={
        "Content-Type": "application/json", "Accept": "application/json, text/event-stream",
        "x-api-key": os.environ.get("MCP_API_KEY", ""),
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())["result"]["structuredContent"]


def catalog() -> dict:
    import server
    return {name: {"team": o["team"], "routing_rule": o.get("routing_rule", "")}
            for name, o in server._load("ownership.json").items()}


# ---------- graph nodes ----------

def node(state: dict, name: str, fn, **inputs):
    start = time.time()
    output = fn(**inputs)
    state["trace"].append({"node": name, "input": inputs, "output": output,
                           "ms": int((time.time() - start) * 1000)})
    save(state)
    return output


def triage(alert: dict) -> dict:
    """Deterministic: seasonal baseline + known external events decide, not an LLM."""
    if alert.get("source") != "biz-metric-alert":
        return {"verdict": "INCIDENT", "reason": "infrastructure alert - always investigated"}
    result = mcp_call("explain_deviation", {
        "metric": alert["metric"], "observed": alert["observed"],
        "timestamp": alert["window_end"], "market": alert.get("market", "KR"),
    })
    mapping = {"WITHIN_NORMAL_RANGE": "EXPECTED_EVENT", "EXPLAINED_BY_EXTERNAL_EVENT": "EXPECTED_EVENT",
               "UNEXPLAINED_ANOMALY": "INCIDENT"}
    verdict = mapping.get(result.get("verdict"), "INCIDENT")  # unknown metric -> investigate (fail safe)
    events = [e["event"] for e in result.get("concurrent_events", [])]
    return {"verdict": verdict, "detail": result.get("verdict", result.get("error")),
            "deviation_pct": result.get("deviation_vs_seasonal_pct"),
            "residual_pct": result.get("residual_after_events_pct"), "events": events}


def investigate(alert: dict, incident_id: str, triage_result: dict) -> dict:
    """Hand the orchestrator's verdict to DevOps Agent so it spends its time on the RCA,
    not on re-classifying the alert with context it may not have."""
    payload = build_payload(alert)
    events = ", ".join(triage_result.get("events", [])) or "none"
    description = (
        f"{payload['description']}\n\n"
        "Triage already done by the orchestrator (do not re-classify):\n"
        f"- Verdict: {triage_result['verdict']} ({triage_result.get('detail')})\n"
        f"- Deviation vs seasonal baseline: {triage_result.get('deviation_pct')}%; "
        f"residual after known external events: {triage_result.get('residual_pct')}%\n"
        f"- Concurrent external events already accounted for: {events}\n"
        "Focus on the root cause: what changed or failed, the evidence for it, the hypotheses "
        "you ruled out, and which service the evidence points to."
    )
    return devops_agent_tool.start_investigation(
        payload["title"], description, payload["priority"], client_token=incident_id)


def route(service: str) -> dict:
    owner = mcp_call("get_service_owner", {"service": service})
    return owner if "error" not in owner else {"team": "unassigned", "service": service, **owner}


def domain_verify(owner: dict, title: str, rca: dict) -> dict:
    import domain_agent
    return domain_agent.ask(owner, catalog(), title, rca).model_dump()


# ---------- state ----------

def path_for(incident_id: str) -> Path:
    return RUNS / f"{incident_id}.json"


def save(state: dict):
    RUNS.mkdir(parents=True, exist_ok=True)
    path_for(state["incident_id"]).write_text(json.dumps(state, ensure_ascii=False, indent=2, default=str))


def load_states() -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted(RUNS.glob("*.json"))] if RUNS.exists() else []


def output_of(state: dict, name: str):
    return next((s["output"] for s in reversed(state["trace"]) if s["node"] == name), None)


# ---------- commands ----------

def cmd_start(samples: list[str]):
    for sample in samples:
        alert = fill_window(json.loads(Path(sample).read_text(encoding="utf-8")))
        incident_id = f"{Path(sample).stem}-{int(time.time())}"
        state = {"incident_id": incident_id, "sample": Path(sample).stem, "alert": alert, "trace": []}
        verdict = node(state, "triage", triage, alert=alert)
        line = f"{incident_id:<48} triage={verdict['verdict']:<15} {verdict.get('detail', '')}"
        if verdict["verdict"] == "INCIDENT":
            task = node(state, "investigate", investigate, alert=alert, incident_id=incident_id,
                        triage_result=verdict)
            line += f"  → DevOps Agent task {task['task_id']} ({task['status']})"
        else:
            line += f"  → closed without investigation ({', '.join(verdict.get('events', [])) or 'normal range'})"
        print(line)


def cmd_status():
    for state in load_states():
        task = output_of(state, "investigate")
        if not task:
            print(f"{state['incident_id']:<48} {output_of(state, 'triage')['verdict']}")
            continue
        status = devops_agent_tool.get_status(task["task_id"])
        extra = f" → primary {status['primary_task_id']}" if status["status"] == "LINKED" else ""
        print(f"{state['incident_id']:<48} {status['status']}{extra}")


def finish_one(state: dict, wait: bool) -> dict | None:
    verdict = output_of(state, "triage")
    task = output_of(state, "investigate")
    alert = state["alert"]
    if output_of(state, "domain_verify") or (not task and output_of(state, "route")):
        pass  # already finished
    elif not task:
        node(state, "route", route, service=alert.get("service", "unknown"))
    else:
        status = (devops_agent_tool.wait(task["task_id"], on_poll=lambda s: print(f"  {state['incident_id']}: {s['status']}"))
                  if wait else devops_agent_tool.get_status(task["task_id"]))
        if status["status"] == "LINKED" and status["primary_task_id"]:
            status = devops_agent_tool.get_status(status["primary_task_id"])
        if status["status"] not in DONE:
            print(f"{state['incident_id']:<48} still {status['status']} - run `finish` again later")
            return None
        rca = node(state, "collect_rca", devops_agent_tool.get_result, task_id=status["task_id"])
        owner = node(state, "route", route, service=alert.get("service", "unknown"))
        node(state, "domain_verify", domain_verify, owner=owner, title=build_payload(alert)["title"], rca=rca)

    owner = output_of(state, "route") or {}
    decision = output_of(state, "domain_verify") or {}
    rca = output_of(state, "collect_rca") or {}
    if not task:
        evidence = [f"{verdict.get('detail')}: deviation {verdict.get('deviation_pct')}%, "
                    f"residual after events {verdict.get('residual_pct')}%"] + verdict.get("events", [])
        root_cause = "Expected business fluctuation: " + (", ".join(verdict.get("events", [])) or "seasonality")
    else:
        evidence = decision.get("evidence", []) + [f[:300] for f in rca.get("findings", [])[:5]]
        root_cause = (rca.get("summary") or "")[:2000] or "; ".join(rca.get("gaps", []))[:2000]
    verdict_label = verdict["verdict"]
    if task and decision.get("decision") == "NEED_MORE_INFO":
        verdict_label = "INCONCLUSIVE"
    return {
        "incident_id": state["sample"],
        "run_id": state["incident_id"],
        "verdict": verdict_label,
        "owner_team": decision.get("owner_team") or owner.get("team"),
        "proposed_team": owner.get("team"),
        "domain_decision": decision.get("decision"),
        "root_cause": root_cause,
        "evidence": evidence,
        "devops_agent_task": task["task_id"] if task else None,
    }


def cmd_finish(wait: bool, out: str):
    rows = [row for row in (finish_one(s, wait) for s in load_states()) if row]
    with open(out, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    for row in rows:
        moved = "" if row["owner_team"] == row["proposed_team"] else f" (proposed {row['proposed_team']})"
        print(f"{row['incident_id']:<34} {row['verdict']:<15} → {row['owner_team']}{moved}  "
              f"[{row['domain_decision'] or 'no RCA needed'}]")
    print(f"\n{len(rows)} result(s) → {out}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("start"); p.add_argument("samples", nargs="+")
    sub.add_parser("status")
    p = sub.add_parser("finish"); p.add_argument("--wait", action="store_true")
    p.add_argument("--out", default=str(HERE / "results.jsonl"))
    p = sub.add_parser("run"); p.add_argument("sample")
    p.add_argument("--out", default=str(HERE / "results.jsonl"))
    p = sub.add_parser("reset")
    args = parser.parse_args()

    if args.cmd == "start":
        cmd_start(args.samples)
    elif args.cmd == "status":
        cmd_status()
    elif args.cmd == "finish":
        cmd_finish(args.wait, args.out)
    elif args.cmd == "run":
        cmd_start([args.sample])
        cmd_finish(True, args.out)
    elif args.cmd == "reset":
        for p in RUNS.glob("*.json"):
            p.unlink()
        print("cleared", RUNS)
    return 0


if __name__ == "__main__":
    sys.exit(main())
