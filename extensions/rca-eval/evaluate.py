"""Measure how trustworthy agent triage is: verdict, routing and root-cause accuracy.

Inputs (JSONL, joined on incident_id):
  ground truth   {"incident_id", "true_verdict", "true_owner_team", "true_root_cause"}
  agent results  {"incident_id", "verdict", "owner_team", "root_cause", "evidence": [...]}

Verdicts: INCIDENT | EXPECTED_EVENT | INCONCLUSIVE

Deterministic metrics (no LLM):
  - verdict accuracy + confusion matrix (incident vs. expected-event discrimination)
  - routing accuracy / misrouting rate on true incidents
  - evidence coverage (incidents routed with >= --min-evidence evidence items)
Optional --judge: an LLM grades whether each root cause matches the postmortem
(MATCH / PARTIAL / MISS) using Claude on Amazon Bedrock.

Usage:
  python3 evaluate.py samples/ground_truth.jsonl samples/agent_results.jsonl
  python3 evaluate.py samples/ground_truth.jsonl samples/agent_results.jsonl --judge --out report.md
"""


from __future__ import annotations
import argparse
import json
import os
import sys
from collections import Counter

VERDICTS = ["INCIDENT", "EXPECTED_EVENT", "INCONCLUSIVE"]
DEFAULT_JUDGE_MODEL = os.environ.get("JUDGE_MODEL", "anthropic.claude-opus-5-5")

JUDGE_SYSTEM = (
    "You grade incident root-cause analyses against the confirmed postmortem root cause. "
    "MATCH: the analysis names the same causal mechanism and component. "
    "PARTIAL: right component or symptom chain but the mechanism is missing or vague, or the true "
    "cause is listed among several equally weighted hypotheses. "
    "MISS: a different cause, or only restates the symptom. "
    "Judge the causal claim, not wording or level of detail."
)


def load_jsonl(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    return {row["incident_id"]: row for row in rows}


def judge_root_causes(pairs: list[tuple[str, str, str]], model: str) -> dict:
    """Grade (incident_id, truth, predicted) triples. Returns {incident_id: (grade, rationale)}."""
    from typing import Literal

    from anthropic import AnthropicBedrockMantle
    from pydantic import BaseModel

    class Grade(BaseModel):
        grade: Literal["MATCH", "PARTIAL", "MISS"]
        rationale: str

    client = AnthropicBedrockMantle(aws_region=os.environ.get("AWS_REGION", "us-east-1"))
    grades = {}
    for incident_id, truth, predicted in pairs:
        response = client.messages.parse(
            model=model,
            max_tokens=2000,
            output_config={"effort": "low"},
            system=JUDGE_SYSTEM,
            messages=[{
                "role": "user",
                "content": (
                    f"<postmortem_root_cause>{truth}</postmortem_root_cause>\n"
                    f"<agent_root_cause>{predicted}</agent_root_cause>\n"
                    "Grade the agent root cause."
                ),
            }],
            output_format=Grade,
        )
        if response.stop_reason == "refusal" or response.parsed_output is None:
            grades[incident_id] = ("ERROR", f"judge returned stop_reason={response.stop_reason}")
        else:
            grades[incident_id] = (response.parsed_output.grade, response.parsed_output.rationale)
    return grades


def pct(n: int, d: int) -> str:
    return f"{n / d * 100:.1f}% ({n}/{d})" if d else "n/a (0)"


def evaluate(truth: dict, results: dict, min_evidence: int, judge: bool, model: str) -> str:
    missing = sorted(set(truth) - set(results))
    ids = sorted(set(truth) & set(results))

    confusion = Counter()
    verdict_ok = 0
    incidents = routed_ok = evidenced = 0
    rows = []
    for i in ids:
        t, r = truth[i], results[i]
        tv, rv = t["true_verdict"], r.get("verdict", "INCONCLUSIVE")
        confusion[(tv, rv)] += 1
        verdict_ok += tv == rv
        route = ""
        if tv == "INCIDENT":
            incidents += 1
            ok = r.get("owner_team") == t["true_owner_team"]
            routed_ok += ok
            evidenced += ok and len(r.get("evidence", [])) >= min_evidence
            route = "OK" if ok else f"MISROUTED -> {r.get('owner_team')}"
        rows.append([i, tv, rv, route])

    grades = {}
    if judge:
        pairs = [(i, truth[i]["true_root_cause"], results[i].get("root_cause", ""))
                 for i in ids if truth[i]["true_verdict"] == "INCIDENT"]
        grades = judge_root_causes(pairs, model)

    out = ["# Agent triage evaluation", ""]
    out += [f"- Incidents evaluated: {len(ids)}" + (f" (missing agent results: {', '.join(missing)})" if missing else "")]
    out += [f"- **Verdict accuracy** (incident vs. expected event): {pct(verdict_ok, len(ids))}"]
    out += [f"- **Routing accuracy** on true incidents: {pct(routed_ok, incidents)}"]
    out += [f"- **Misrouting rate**: {pct(incidents - routed_ok, incidents)}"]
    out += [f"- **Routed with evidence** (>= {min_evidence} items): {pct(evidenced, incidents)}"]
    if grades:
        c = Counter(g for g, _ in grades.values())
        out += [f"- **Root cause (LLM judge, {model})**: MATCH {pct(c['MATCH'], len(grades))}, "
                f"PARTIAL {c['PARTIAL']}, MISS {c['MISS']}, ERROR {c['ERROR']}"]

    out += ["", "## Verdict confusion matrix (rows = truth, cols = agent)", ""]
    out += ["| truth \\ agent | " + " | ".join(VERDICTS) + " |", "|---|" + "---|" * len(VERDICTS)]
    for tv in [v for v in VERDICTS if v != "INCONCLUSIVE" or any(k[0] == v for k in confusion)]:
        out += [f"| {tv} | " + " | ".join(str(confusion[(tv, av)]) for av in VERDICTS) + " |"]

    out += ["", "## Per incident", "", "| incident | truth | agent | routing | root cause grade |", "|---|---|---|---|---|"]
    for i, tv, rv, route in rows:
        g = grades.get(i)
        out += [f"| {i} | {tv} | {rv} | {route} | {f'{g[0]}: {g[1]}' if g else ''} |"]
    return "\n".join(out) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("ground_truth")
    parser.add_argument("agent_results")
    parser.add_argument("--min-evidence", type=int, default=2)
    parser.add_argument("--judge", action="store_true", help="grade root causes with Claude on Bedrock")
    parser.add_argument("--model", default=DEFAULT_JUDGE_MODEL, help="Bedrock model id for the judge")
    parser.add_argument("--out", help="write the markdown report to this file")
    args = parser.parse_args()

    report = evaluate(load_jsonl(args.ground_truth), load_jsonl(args.agent_results),
                      args.min_evidence, args.judge, args.model)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(report)
    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
