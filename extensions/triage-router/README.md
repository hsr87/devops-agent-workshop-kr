# triage-router

기존 메인 에이전트에 AWS DevOps Agent를 **RCA tool**로 붙이는 최소 예제입니다. 판별과 라우팅은 코드가 결정적으로 처리하고, 원인 분석만 DevOps Agent API에 맡깁니다.

```
alert → triage (baseline + 이벤트, 결정적) ─EXPECTED_EVENT→ 종료
                     └─INCIDENT→ investigate (DevOps Agent API) → route (서비스 카탈로그)
                                 → domain_verify (도메인 에이전트 ACCEPT/REJECT) → results.jsonl
```

```bash
source ~/.ext-workshop.env            # AGENT_SPACE_ID, EXT_PYTHON
$EXT_PYTHON router.py start ../alert-forwarder/samples/impressions-*.json ../alert-forwarder/samples/order-errors-spike.json
$EXT_PYTHON router.py status
$EXT_PYTHON router.py finish --wait   # → results.jsonl, runs/*.json (노드별 trace)
python3 ../rca-eval/evaluate.py ground_truth.jsonl results.jsonl
$EXT_PYTHON router.py reset           # runs/ 비우기
```

| 파일 | 역할 |
|---|---|
| `router.py` | 오케스트레이터. 노드별 input/output/소요 시간을 `runs/<id>.json` 에 기록 |
| `devops_agent_tool.py` | `create_backlog_task` / `get_backlog_task` / `list_executions` + `list_journal_records` 래퍼. `LINKED` 면 primary 조사를 따라감 |
| `domain_agent.py` | 도메인 서브에이전트 (Bedrock Claude, structured output). 기존 서브에이전트 호출로 교체할 자리 |
| `ground_truth.jsonl` | 세 샘플 시나리오의 정답 |

환경 변수: `AGENT_SPACE_ID`(필수), `AWS_REGION`(기본 us-east-1), `MCP_URL`/`MCP_API_KEY`(설정하면 판별·owner 조회를 배포된 확장 B MCP 서버로 호출), `DOMAIN_AGENT_MODEL`(기본 `anthropic.claude-opus-5-5`).

필요 권한: DevOps Agent의 `CreateBacklogTask`, `GetBacklogTask`, `ListExecutions`, `ListJournalRecords` API, Bedrock 모델 호출.
