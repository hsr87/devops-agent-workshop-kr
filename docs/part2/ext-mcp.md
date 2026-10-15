# 확장 B · 이벤트 컨텍스트 MCP 서버

**목표:** 텔레메트리에는 없는 **비즈니스 맥락**(경기 일정, 프로모션, 공휴일, 계절성 baseline, 서비스 owner)을 MCP로 DevOps Agent에 제공합니다. 이를 통해 "진짜 장애인가, 예상된 변동인가"를 판별하고 **근거를 갖고 라우팅**하게 합니다.

코드: [`extensions/event-context-mcp`](https://github.com/hsr87/devops-agent-workshop-kr/tree/main/extensions/event-context-mcp) — 외부 의존성 없는 Python 단일 파일이며, Streamable HTTP를 stateless로 처리합니다.

## 제공하는 tool (모두 read-only)

| tool | 하는 일 | 연결되는 질문 |
|---|---|---|
| `explain_deviation` | 관측값을 계절성 baseline과 동시간대 이벤트 영향으로 보정한 뒤 판정: `WITHIN_NORMAL_RANGE` / `EXPLAINED_BY_EXTERNAL_EVENT` / `UNEXPLAINED_ANOMALY` | 인시던트 판별 |
| `list_external_events` | 시간 범위와 겹치는 경기, 프로모션, 공휴일과 각각의 예상 영향(%) | 인시던트 판별 |
| `get_metric_baseline` | 요일과 시간대별 기대값 및 정상 범위 | 인시던트 판별 |
| `get_service_owner` | owner 팀, on-call 채널, upstream/downstream, 라우팅 규칙 | 도메인 라우팅 |

`data/*.json` 은 **mock 데이터**입니다. 운영 환경에서는 이 함수들이 사내 이벤트 캘린더, 메트릭 저장소, 서비스 카탈로그를 조회하도록 바꾸면 됩니다.

## 실습

### 1) 로컬에서 동작 확인 (VS Code IDE 터미널)

```bash
cd $EXT_REPO/extensions/event-context-mcp
MCP_API_KEY=dev python3 server.py --port 8765 & sleep 1
MCP_URL=http://localhost:8765/mcp MCP_API_KEY=dev ./test_mcp.sh
kill %1
```

```text
== explain_deviation (-26%, live match)
EXPLAINED_BY_EXTERNAL_EVENT -26.0 -1.3
== explain_deviation (-62%, live match)
UNEXPLAINED_ANOMALY -62.0 -49.3
== get_service_owner
order-api commerce-order-team #order-oncall
```

### 2) AWS에 배포 (Lambda + API Gateway HTTP API)

DevOps Agent는 **공개 HTTPS** 로 접근할 수 있는 **Streamable HTTP** MCP 서버만 지원합니다. VPC 내부 서버는 지원하지 않습니다.

```bash
./deploy.sh                       # 엔드포인트와 API key를 .mcp-endpoint.env 에 저장
set -a; source .mcp-endpoint.env; set +a
./test_mcp.sh                     # 원격 엔드포인트 스모크 테스트
```

### 3) DevOps Agent에 등록

```bash
source ~/.ext-workshop.env
./register.sh                     # 계정 단위로 MCP 서버를 등록하고, Agent Space에 tool 4개를 READ_ONLY로 허용
```

콘솔에서 해도 결과는 같습니다.

1. **Settings → MCP servers → Add**
2. Endpoint: `.mcp-endpoint.env` 의 `MCP_URL`
3. Auth: **API key**, header 이름은 `x-api-key`
4. Agent Space → **기능**(Capabilities) 탭에서 tool 허용

!!! success "Workshop Studio 계정에서는 등록됩니다 (사전 검증에서 확인)"
    일부 일반 계정에서는 *"Only external accounts and exempted accounts are allowed at this time"* 오류로 등록이 거부됩니다. 하지만 **Workshop Studio 이벤트 계정에서는 등록과 Agent Space 연결이 모두 성공**했습니다. `register.sh` 는 다시 실행해도 안전합니다. 이미 등록돼 있으면 그 서버를 재사용합니다. → [사전 검증 결과](../facilitator/test-report.md)

### 4) 효과 확인 {#effect}

MCP를 연결한 뒤 [확장 A](ext-alert.md)로 **-26% 알림을 웹훅으로** 보냅니다. 이번에는 메인 에이전트의 판별 없이 **DevOps Agent가 스스로** 판단합니다.

```bash
cd $EXT_REPO/extensions/alert-forwarder
python3 send_test_alert.py samples/impressions-drop-during-match.json
aws devops-agent list-backlog-tasks --agent-space-id "$AGENT_SPACE_ID" --query 'tasks[].[title,status]' --output table
```

결과는 **같은 Agent Space에 최근 광고 조사가 있느냐**에 따라 두 가지로 나옵니다.

| 상황 | -26% 알림의 상태 | 결과를 보는 곳 |
|---|---|---|
| 최근 광고 조사 없음 (진행자 데모 계정) | 새 조사 | 그 조사의 결론: *"Verdict: **EXPECTED_EVENT — not an incident**"* |
| [메인 에이전트 실습](ext-router.md)을 방금 끝냄 (참가자 계정) | **`LINKED`** → -62% 조사가 재조사 | -62% 조사의 새 요약: *"ad_impressions drop recovering (−62% → −26%)"* |

두 경우 모두 조사 기록에서 `explain_deviation`, `get_metric_baseline`, `get_service_owner` 호출을 확인할 수 있습니다. 이것이 MCP가 연결됐다는 증거입니다. MCP가 없을 때는 같은 알림에 대해 *"event-context MCP tools are not wired into this space"* 를 `investigation_gap` 으로 남기고 판단을 유보했습니다.

!!! warning "참가자 계정에서는 `LINKED` 가 정상입니다 (사전 검증 2회차에서 확인)"
    메인 에이전트 실습의 -62% 조사가 **이미 완료된 뒤**(조사 시작 17분 뒤)에 -26% 알림을 보냈는데도 `LINKED` 되었습니다. 연결 사유는 다음과 같았습니다.

    > *"Same service (ads-serving), same metric (ad_impressions), same market (KR) … a continuation of the same ongoing ad_impressions degradation, with the deviation now at -26% vs the earlier -62%."*

    이 장면은 그대로 토론 소재가 됩니다. 알림이 연달아 오면 DevOps Agent는 **새 조사를 만들지 않고 기존 장애의 경과로 해석**합니다. `EXPECTED_EVENT` 결론 화면은 [진행자 데모](../facilitator/index.md)로 보여 줍니다.

## 운영에 적용할 때

- 조사 품질은 **tool 설명**(description)에 크게 좌우됩니다. "언제 이 tool을 먼저 불러야 하는지"를 설명에 명시하세요. 예: `Call this first when an alert is about a business metric.`
- 계정 단위로 등록한 MCP 서버를 **Agent Space마다 필요한 tool만 허용**하세요. 자격 증명은 read-only 권한만 갖게 하는 것이 권장 사항입니다.
- 인증은 API key 외에도 Bearer token, OAuth client credentials, SigV4(`mcpserversigv4`)를 지원합니다.
