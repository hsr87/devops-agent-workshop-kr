"""Domain sub-agent: "is this really our team's problem?"

The orchestrator proposes an owner from the service catalog. The domain agent of that
team reads the DevOps Agent RCA and either ACCEPTs (with evidence) or REJECTs and names
the team it thinks owns the cause. This is the step where most misrouting is caught,
and because the input and output are recorded, it can be measured.

Replace `ask()` with a call to your existing domain agent (HTTP, A2A, Lambda...).
"""


from __future__ import annotations
import json
import os
from typing import Literal

from pydantic import BaseModel

MODEL = os.environ.get("DOMAIN_AGENT_MODEL", "anthropic.claude-opus-5-5")


class Decision(BaseModel):
    decision: Literal["ACCEPT", "REJECT", "NEED_MORE_INFO"]
    owner_team: str
    reason: str
    evidence: list[str]


def _system(owner: dict, catalog: dict) -> str:
    return (
        f"You are the on-call domain agent for {owner['team']} "
        f"(service {owner['service']}: {owner.get('domain', '')}).\n"
        f"Your routing rule: {owner.get('routing_rule', 'n/a')}.\n"
        f"Upstream: {owner.get('upstream', [])}, downstream: {owner.get('downstream', [])}.\n"
        f"Service catalog (service -> team, routing rule): {json.dumps(catalog, ensure_ascii=False)}\n\n"
        "Given an alert and an RCA from AWS DevOps Agent, decide who owns the fix. Judge "
        "ownership of the cause the RCA identifies, not whether the alert's metric itself "
        "could be re-observed (alert metrics often live outside the investigated account).\n"
        "- ACCEPT when the RCA identifies a cause with concrete evidence (code, logs, config, "
        "deployments, metrics) in your service. Mention open questions in the reason.\n"
        "- REJECT when that evidence points to another team's service; set owner_team to it.\n"
        "- NEED_MORE_INFO when the RCA confirms no cause, or only lists candidate services as "
        "hypotheses without confirming evidence. Keep owner_team as your own team.\n"
        "Evidence means observations of the named service's own resources (its metrics, logs, "
        "code, deployments). Routing rules, catalog descriptions, the alert text, and telemetry "
        "from a different service are not evidence for or against a service; a cause supported "
        "only by them is a hypothesis.\n"
        "Cite only evidence that appears in the RCA; never invent evidence."
    )


def ask(owner: dict, catalog: dict, alert_title: str, rca: dict) -> Decision:
    from anthropic import AnthropicBedrockMantle

    client = AnthropicBedrockMantle(aws_region=os.environ.get("AWS_REGION", "us-east-1"))
    rca_text = (
        f"Summary:\n{rca.get('summary') or '(no summary)'}\n\n"
        f"Findings:\n" + "\n".join(f"- {f}" for f in rca.get("findings", [])[:10]) + "\n\n"
        f"Investigation gaps:\n" + "\n".join(f"- {g}" for g in rca.get("gaps", [])[:5])
    )
    response = client.messages.parse(
        model=MODEL,
        max_tokens=2000,
        output_config={"effort": "low"},
        system=_system(owner, catalog),
        messages=[{"role": "user", "content": f"Alert: {alert_title}\n\nRCA:\n{rca_text[:12000]}"}],
        output_format=Decision,
    )
    if response.parsed_output is None:
        return Decision(decision="NEED_MORE_INFO", owner_team=owner["team"],
                        reason=f"domain agent returned no decision ({response.stop_reason})", evidence=[])
    return response.parsed_output
