# event-context-mcp

DevOps Agent가 조사 중에 호출하는 MCP 서버입니다. 외부 이벤트(경기, 프로모션, 공휴일), 계절성 baseline, 서비스 owner를 제공합니다. MCP Streamable HTTP를 stateless JSON 응답으로 구현했고, 외부 의존성은 없습니다.

| tool | 설명 |
|---|---|
| `explain_deviation` | 관측값 → `WITHIN_NORMAL_RANGE` / `EXPLAINED_BY_EXTERNAL_EVENT` / `UNEXPLAINED_ANOMALY` |
| `list_external_events` | 시간 범위와 겹치는 이벤트와 예상 영향(%) |
| `get_metric_baseline` | 요일과 시간대별 기대값 및 정상 범위 |
| `get_service_owner` | owner 팀, on-call 채널, 의존성, 라우팅 규칙 |

```bash
MCP_API_KEY=dev python3 server.py --port 8765 & sleep 1  # 로컬 (8080은 VS Code IDE가 사용 중)
MCP_URL=http://localhost:8765/mcp MCP_API_KEY=dev ./test_mcp.sh
./deploy.sh && set -a && source .mcp-endpoint.env && set +a && ./test_mcp.sh   # Lambda + HTTP API
AGENT_SPACE_ID=... ./register.sh                          # DevOps Agent 등록 + tool 허용
```

`data/*.json` 은 mock 데이터입니다. 가이드: https://hsr87.github.io/devops-agent-workshop-kr/part2/ext-mcp/
