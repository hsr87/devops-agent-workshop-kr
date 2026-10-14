"""DevOps Agent as a *tool* of your existing orchestrator.

Three calls are all you need:
  start_investigation()  -> create_backlog_task (taskType=INVESTIGATION)
  get_status()           -> get_backlog_task (status, LINKED primary, statusReason)
  get_result()           -> list_executions + list_journal_records (summary, findings, gaps)

Wrap these in whatever your framework calls a tool (Strands @tool, LangGraph node,
a plain function in your main agent). The original Lab 3 `aidevops_client.py`
does the same thing with a polling loop.
"""


from __future__ import annotations
import json
import os
import time

import boto3

TERMINAL = {"COMPLETED", "FAILED", "TIMED_OUT", "CANCELED", "SKIPPED"}
RESULT_RECORD_TYPES = ("investigation_summary_md", "finding", "investigation_gap", "symptom")


def _client():
    return boto3.client("devops-agent", region_name=os.environ.get("AWS_REGION", "us-east-1"))


def _space() -> str:
    space = os.environ.get("AGENT_SPACE_ID")
    if not space:
        raise SystemExit("AGENT_SPACE_ID is not set - run `source ~/.ext-workshop.env`")
    return space


def start_investigation(title: str, description: str, priority: str = "HIGH",
                        client_token: str | None = None) -> dict:
    kwargs = {
        "agentSpaceId": _space(),
        "taskType": "INVESTIGATION",
        "title": title[:512],
        "description": description,
        "priority": priority,
    }
    if client_token:
        kwargs["clientToken"] = client_token  # idempotent retries from the orchestrator
    task = _client().create_backlog_task(**kwargs)["task"]
    return {"task_id": task["taskId"], "status": task["status"]}


def get_status(task_id: str) -> dict:
    task = _client().get_backlog_task(agentSpaceId=_space(), taskId=task_id)["task"]
    return {
        "task_id": task_id,
        "status": task["status"],
        "primary_task_id": task.get("primaryTaskId"),
        "status_reason": task.get("statusReason"),
    }


def wait(task_id: str, timeout_s: int = 1200, poll_s: int = 15, on_poll=None) -> dict:
    """Poll until the task is terminal. A LINKED task is followed to its primary task."""
    deadline = time.time() + timeout_s
    while True:
        status = get_status(task_id)
        if on_poll:
            on_poll(status)
        if status["status"] == "LINKED" and status["primary_task_id"]:
            task_id = status["primary_task_id"]
        elif status["status"] in TERMINAL:
            return status
        if time.time() > deadline:
            return {**status, "status": "WAIT_TIMEOUT"}
        time.sleep(poll_s)


def _content(record) -> object:
    content = record.get("content")
    if isinstance(content, str):
        try:
            return json.loads(content)
        except ValueError:
            return content
    return content


def _text(content) -> str:
    """Journal content shapes vary by record type; pull out readable text."""
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        for key in ("markdown", "summary", "text", "description", "title", "content"):
            if isinstance(content.get(key), str):
                return content[key]
        if isinstance(content.get("data"), (dict, str)):
            return _text(content["data"])
    return json.dumps(content, ensure_ascii=False)


def get_result(task_id: str) -> dict:
    """Collect the investigation summary, findings and gaps of a (primary) task."""
    client, space = _client(), _space()
    executions = client.list_executions(agentSpaceId=space, taskId=task_id).get("executions", [])
    out = {"task_id": task_id, "summary": "", "findings": [], "gaps": [], "symptoms": []}
    for execution in executions:
        token = None
        while True:
            kwargs = {"agentSpaceId": space, "executionId": execution["executionId"], "limit": 100}
            if token:
                kwargs["nextToken"] = token
            page = client.list_journal_records(**kwargs)
            for record in page.get("records", []):
                kind = record.get("recordType")
                if kind not in RESULT_RECORD_TYPES:
                    continue
                text = _text(_content(record)).strip()
                if kind == "investigation_summary_md":
                    out["summary"] = text  # keep the latest summary (re-investigations append)
                elif kind == "finding":
                    out["findings"].append(text)
                elif kind == "investigation_gap":
                    out["gaps"].append(text)
                else:
                    out["symptoms"].append(text)
            token = page.get("nextToken")
            if not token:
                break
    return out
